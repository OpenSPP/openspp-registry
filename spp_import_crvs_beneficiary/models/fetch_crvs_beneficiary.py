import logging
import uuid

import requests
from dateutil import parser

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import safe_eval

from ..models import constants
from ..tools import calculate_signature

_logger = logging.getLogger(__name__)

DATA_SOURCE_NAME = "CRVS"
DATA_SOURCE_SEARCH_PATH_NAME = "Registry Sync Search"


class FetchDomainFilter(models.TransientModel):
    _name = "spp.fetch.domain.filter"
    _description = "Fetch Domain Filter"

    birthdate = fields.Date("Birth Date")


class SPPFetchCRVSBeneficiary(models.Model):
    _name = "spp.fetch.crvs.beneficiary"
    _description = "Fetch CRVS Beneficiary"

    name = fields.Char("Search Criteria Name", required=True)

    domain = fields.Text(default="[]", required=True)

    done_imported = fields.Boolean()
    imported_individual_ids = fields.One2many(
        "spp.crvs.imported.individuals",
        "fetch_crvs_id",
        "Imported Individuals",
        readonly=True,
    )

    TIMEOUT = 10

    @api.model
    def get_data_source(self):
        self.ensure_one()

        data_source = self.env["spp.data.source"].search(
            [("name", "=", DATA_SOURCE_NAME)], limit=1
        )

        if not data_source:
            raise ValidationError(
                _("No data source named {data_source} is configured!").format(
                    data_source=DATA_SOURCE_NAME
                )
            )

        paths = {}

        for path_id in data_source.data_source_path_ids:
            paths[path_id.name] = path_id.path

        if DATA_SOURCE_SEARCH_PATH_NAME not in paths:
            raise ValidationError(
                _("No path in data source named {path} is configured!").format(
                    path=DATA_SOURCE_SEARCH_PATH_NAME
                )
            )

        return data_source, paths

    def get_crvs_search_url(self, data_source_id, paths):
        url = data_source_id.url
        search_path = paths.get(DATA_SOURCE_SEARCH_PATH_NAME)

        return f"{url}{search_path}"

    def get_headers_for_request(self):
        return {
            "Content-Type": "application/json",
        }

    def get_header_for_body(self, crvs_version, today_isoformat, message_id):
        sender_id = "sender1"
        receiver_id = "receiver1"
        total_count = 1
        return {
            "version": crvs_version,
            "message_id": message_id,
            "message_ts": today_isoformat,
            "action": "search",
            "sender_id": sender_id,
            "sender_uri": "",
            "receiver_id": receiver_id,
            "total_count": total_count,
            "encryption_algorithm": "",
        }

    def get_query(self):
        queries = []
        domain = safe_eval.safe_eval(self.domain)

        if not domain:
            raise ValidationError(_("Add atleast one filter."))

        for dom in domain:
            if isinstance(dom, list) and len(dom) == 3:
                field_name = constants.FIELD_MAPPING.get(dom[0])
                operator = constants.OPERATION_MAPPING.get(dom[1])
                if field_name and operator:
                    value = dom[2]
                    queries.append(
                        {
                            "expression1": {
                                "attribute_name": field_name,
                                "operator": operator,
                                "attribute_value": value,
                            }
                        }
                    )
        return queries

    def get_search_request(self, crvs_version, reference_id, today_isoformat):
        search_requests = {
            "version": crvs_version,
            "reference_id": reference_id,
            "timestamp": today_isoformat,
            "registry_type": "civil",
            "search_criteria": {
                "reg_event_type": {
                    "value": "1",
                },
                "query_type": constants.PREDICATE,
                "result_record_type": {
                    "value": "person",
                },
                "query": self.get_query(),
            },
        }

        return search_requests

    def get_message(self, crvs_version, today_isoformat, transaction_id, reference_id):
        # Define Search Requests
        search_request = self.get_search_request(
            crvs_version, reference_id, today_isoformat
        )

        return {
            "transaction_id": transaction_id,
            "search_request": search_request,
        }

    def get_data(self, signature, header, message):
        return {"signature": signature, "header": header, "message": message}

    def get_partner_and_clean_identifier(
        self, identifiers, identifier_type_key="type", identifier_value_key="value"
    ):
        clean_identifiers = []
        partner_id = None
        # get existing record if there's any
        for identifier in identifiers:
            identifier_type = identifier.get(identifier_type_key, "")
            identifier_value = identifier.get(identifier_value_key, "")
            if identifier_type and identifier_value:

                # Check if identifier type is already created. Create record if no existing identifier type
                id_type = self.env["g2p.id.type"].search(
                    [("name", "=", identifier_type)], limit=1
                )
                if not id_type:
                    id_type = self.env["g2p.id.type"].create({"name": identifier_type})

                clean_identifiers.append(
                    {"id_type": id_type, "value": identifier_value}
                )

                if not partner_id:
                    reg_id = self.env["g2p.reg.id"].search(
                        [
                            ("id_type", "=", id_type.id),
                            ("value", "=", identifier_value),
                        ],
                        limit=1,
                    )
                    if reg_id:
                        partner_id = reg_id.partner_id

        return partner_id, clean_identifiers

    def get_full_name_format(self, family_name, given_name, middle_name):
        name = ""
        if family_name:
            name += family_name + ", "
        if given_name:
            name += given_name + " "
        if middle_name:
            name += middle_name + " "
        name = name.upper()

        return name

    def get_individual_data(self, record):
        family_name = record.get("familyName", "")
        given_name = record.get("givenName", "")
        middle_name = record.get("middleName", "")
        sex = record.get("sex", "")
        birth_date = record.get("birthDate", "")
        birth_place = record.get("birthPlace", {}).get("address", "")
        try:
            birth_date = parser.parse(birth_date)
        except Exception as e:
            birth_date = False
            _logger.error(e)

        name = self.get_full_name_format(family_name, given_name, middle_name)

        return {
            "name": name,
            "family_name": family_name,
            "given_name": given_name,
            "addl_name": middle_name,
            "gender": sex.title(),
            "birthdate": birth_date,
            "birth_place": birth_place,
            "is_registrant": True,
            "is_group": False,
        }

    def create_or_update_individual(self, partner_id, partner_data):
        if partner_id:
            partner_id.write(partner_data)
        else:
            partner_id = self.env["res.partner"].create(partner_data)

        return partner_id

    def create_registrant_id(self, clean_identifiers, partner_id):
        for clean_identifier in clean_identifiers:
            partner_reg_id = self.env["g2p.reg.id"].search(
                [
                    ("id_type", "=", clean_identifier["id_type"].id),
                    ("partner_id", "=", partner_id.id),
                ]
            )
            if not partner_reg_id:
                reg_data = {
                    "id_type": clean_identifier["id_type"].id,
                    "partner_id": partner_id.id,
                    "value": clean_identifier["value"],
                }
                self.env["g2p.reg.id"].create(reg_data)
        return

    def process_records(
        self, record, identifier_type_key="name", identifier_value_key="identifier"
    ):
        identifiers = record.get("identifier", [])
        (partner_id, clean_identifiers,) = self.get_partner_and_clean_identifier(
            identifiers,
            identifier_type_key=identifier_type_key,
            identifier_value_key=identifier_value_key,
        )

        if partner_id:
            is_created = False
        else:
            is_created = True

        # Instantiate individual data
        partner_data = self.get_individual_data(record)

        # Create or Update individual
        partner_id = self.create_or_update_individual(partner_id, partner_data)

        # Check and Create Registrant ID
        self.create_registrant_id(clean_identifiers, partner_id)

        # Create CRVS Imported Individuals
        crvs_imported_individuals = self.env["spp.crvs.imported.individuals"]
        if not crvs_imported_individuals.search(
            [("fetch_crvs_id", "=", self.id), ("individual_id", "=", partner_id.id)],
            limit=1,
        ):
            crvs_imported_individuals.create(
                {
                    "fetch_crvs_id": self.id,
                    "individual_id": partner_id.id,
                    "is_created": is_created,
                    "is_updated": not is_created,
                }
            )

        return partner_id

    def fetch_crvs_beneficiary(self):

        config_parameters = self.env["ir.config_parameter"].sudo()
        today_isoformat = fields.Datetime.today().isoformat()
        crvs_version = config_parameters.get_param("crvs_version")

        message_id = str(uuid.uuid4())

        # Define Data Source
        data_source_id, paths = self.get_data_source()

        # Define CRVS search url
        full_crvs_search_url = self.get_crvs_search_url(data_source_id, paths)

        # Define headers for post request
        headers = self.get_headers_for_request()

        # Define header
        header = self.get_header_for_body(
            crvs_version,
            today_isoformat,
            message_id,
        )

        # Define message
        message = self.get_message(
            crvs_version,
            today_isoformat,
            transaction_id=message_id,
            reference_id="",
        )

        # Define signature
        signature = calculate_signature(header=header, payload=message)

        # Define data
        data = self.get_data(
            signature,
            header,
            message,
        )

        # POST Request
        response = requests.post(
            full_crvs_search_url,
            headers=headers,
            json=data,
            timeout=self.TIMEOUT,
        )

        # Process response
        if response.ok:
            kind = "success"
            message = _("Successfully Imported CRVS Beneficiaries")

            search_responses = (
                response.json().get("message", {}).get("search_response", [])
            )
            for search_response in search_responses:
                reg_records = search_response.get("data", {}).get("reg_records", [])
                for record in reg_records:
                    identifiers = record.get("identifier", [])
                    if identifiers:
                        partner_id = self.process_records(record)

                        relations = record.get("relations", [])
                        for relation in relations:
                            relation_identifiers = relation.get("identifier", [])
                            is_mother = "Mother" in relation.get("@type", "")
                            if relation_identifiers and is_mother:
                                relation_partner_id = self.process_records(
                                    relation,
                                    identifier_type_key="name",
                                    identifier_value_key="identifier",
                                )

                                # Check if parent have group membership
                                group = None
                                if relation_partner_id.individual_membership_ids:
                                    membership = self.env[
                                        "g2p.group.membership"
                                    ].search(
                                        [
                                            (
                                                "id",
                                                "in",
                                                relation_partner_id.individual_membership_ids.ids,
                                            ),
                                            ("is_created_from_crvs", "=", True),
                                        ],
                                        limit=1,
                                    )
                                    if membership:
                                        group = membership.group

                                # Create group membership
                                if not group:
                                    group = self.env["res.partner"].create(
                                        {
                                            "name": f"{str(relation_partner_id.family_name).title()} Family",
                                            "is_registrant": True,
                                            "is_group": True,
                                            "grp_is_created_from_crvs": True,
                                            "kind": self.env.ref(
                                                "g2p_registry_group.group_kind_family"
                                            ).id,
                                        }
                                    )

                                    # if parent not in group
                                    if not self.env["g2p.group.membership"].search(
                                        [
                                            ("group", "=", group.id),
                                            ("individual", "=", relation_partner_id.id),
                                        ]
                                    ):
                                        # Add parent to group
                                        self.env["g2p.group.membership"].create(
                                            {
                                                "group": group.id,
                                                "individual": relation_partner_id.id,
                                                "kind": [
                                                    (
                                                        4,
                                                        self.env.ref(
                                                            "g2p_registry_membership.group_membership_kind_head"
                                                        ).id,
                                                    )
                                                ],
                                            }
                                        )

                                # If child not in group
                                if not self.env["g2p.group.membership"].search(
                                    [
                                        ("group", "=", group.id),
                                        ("individual", "=", partner_id.id),
                                    ]
                                ):
                                    # Add child to group
                                    self.env["g2p.group.membership"].create(
                                        {
                                            "group": group.id,
                                            "individual": partner_id.id,
                                        }
                                    )

            self.done_imported = True
        else:
            kind = "danger"
            message = response.reason

        action = {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("CRVS"),
                "message": message,
                "sticky": True,
                "type": kind,
                "next": {
                    "type": "ir.actions.act_window_close",
                },
            },
        }
        return action
