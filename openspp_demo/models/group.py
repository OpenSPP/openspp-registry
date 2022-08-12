#
# Copyright (c) 2022 Newlogic.
#
import datetime
import logging

from dateutil.relativedelta import relativedelta

from odoo import fields, models

_logger = logging.getLogger(__name__)

CHILDREN_AGE_LIMIT = 18
ELDERLY_AGE_LIMIT = 65


class G2PGroup(models.Model):
    _inherit = "res.partner"

    """
    Source:

    OK ➢ Households (HH) with children - extracted from demographic data of HH adult members plus child members
    OK ➢ single-headed HH - extracted from demographic data of HH adult members
    OK ➢ female-headed HH - extracted from demographic data of HH adult members
    OK ➢ HH with pregnant/lactating women - extracted from vulnerability criteria
    OK ➢ HH with elderly (including single / elderly-headed HHs) - extracted from demographic
    data of HH adult members
    OK ➢ HHs with disabled (mental or physical) members - extracted from vulnerability criteria
    OK ➢ HHs with members that have chronic illness/medical conditions - extracted from
    vulnerability criteria
"""
    z_crt_grp_num_children = fields.Integer(
        "Number of children",
        compute="_compute_crt_grp_num_children",
        help="Households (HH) with children - extracted from demographic data of "
        "HH adult members plus child members",
        store=True,
    )
    z_crt_grp_num_members = fields.Integer(
        "Number of members", compute="_compute_crt_grp_num_members", store=True
    )
    z_crt_grp_num_adults = fields.Integer(
        "Number of adults", compute="_compute_crt_grp_num_adults", store=True
    )
    z_crt_grp_num_adults_woman = fields.Integer(
        "Number of adults woman",
        compute="_compute_crt_grp_num_adults_woman",
        store=True,
    )
    z_crt_grp_num_elderly = fields.Integer(
        "Number of eldery", compute="_compute_crt_grp_num_eldery", store=True
    )

    z_crt_grp_is_hh_with_children = fields.Boolean(
        "Is household (HH) with children",
        compute="_compute_crt_grp_is_hh_with_children",
        store=True,
    )

    # z_crt_grp_is_hh_with_disabled = fields.Boolean("HHs with disabled (mental or physical) members",
    #                                                compute="_compute_crt_grp_is_hh_with_disabled")

    z_crt_grp_is_hh_with_elderly = fields.Boolean(
        "Is household with elderly",
        compute="_compute_crt_grp_is_hh_with_elderly",
        help="Households (HH) with elderly (including single / elderly-headed "
        "HHs) - extracted from demographic data of HH adult members",
        store=True,
    )

    z_crt_grp_is_hh_with_pregnant_lactating = fields.Boolean(
        "Is household with pregnant/lactating women",
        compute="_compute_crt_grp_is_hh_with_pregnant_lactating",
        help="HH with pregnant/lactating women",
        store=True,
    )

    z_crt_grp_is_hh_with_disabled = fields.Boolean(
        "Is household disabled (mental or physical) members",
        compute="_compute_crt_grp_is_hh_with_disabled",
        help="HHs with disabled (mental or physical) members",
        store=True,
    )

    z_crt_grp_is_hh_with_medical_condition = fields.Boolean(
        "Is household with members that have chronic illness/medical conditions",
        compute="_compute_crt_grp_is_hh_with_medical_condition",
        help="HHs with members that have chronic illness/medical conditions",
        store=True,
    )

    z_crt_grp_is_single_head_hh = fields.Boolean(
        "Is single-headed household",
        compute="_compute_crt_grp_is_single_head_hh",
        help="Single-headed HH - extracted from demographic data of "
        "HH adult members",
        store=True,
    )
    z_crt_grp_is_woman_head_hh = fields.Boolean(
        "Is female-headed household",
        compute="_compute_crt_grp_is_woman_head_hh",
        help="Female-headed HH - extracted from demographic data of "
        "HH adult members",
        store=True,
    )
    z_crt_grp_is_elderly_head_hh = fields.Boolean(
        "Is elderly-headed household",
        compute="_compute_crt_grp_is_eldery_head_hh",
        help="Elderly-headed HHs - "
        "extracted from demographic data of HH adult members",
        store=True,
    )

    def _compute_crt_grp_num_children(self):
        """
        Households (HH) with children
        Returns:

        """
        now = datetime.datetime.now()
        children = now - relativedelta(years=CHILDREN_AGE_LIMIT)
        criteria = [("birthdate", ">=", children)]
        self._compute_count_and_set("z_crt_grp_num_children", None, criteria)

    def _compute_crt_grp_num_eldery(self):
        """
        Number of Eldery in this household
        Returns:

        """
        now = datetime.datetime.now()
        criteria = [("birthdate", "<", now - relativedelta(years=ELDERLY_AGE_LIMIT))]
        self._compute_count_and_set("z_crt_grp_num_elderly", None, criteria)

    def _compute_crt_grp_num_members(self):
        """
        Number of members in this household
        Returns:

        """
        self._compute_count_and_set("z_crt_grp_num_members", None, [])

    def _compute_crt_grp_num_adults(self):
        """
        Number of adults in this household
        Returns:

        """
        now = datetime.datetime.now()
        criteria = [("birthdate", "<", now - relativedelta(years=CHILDREN_AGE_LIMIT))]
        self._compute_count_and_set("z_crt_grp_num_adults", None, criteria)

    def _compute_crt_grp_num_adults_woman(self):
        """
        Number of adults woman in this household
        Returns:

        """
        now = datetime.datetime.now()
        criteria = [
            ("birthdate", "<", now - relativedelta(years=CHILDREN_AGE_LIMIT)),
            ("gender", "=", "Female"),
        ]
        self._compute_count_and_set("z_crt_grp_num_adults_woman", None, criteria)

    def _compute_crt_grp_is_single_head_hh(self):
        """
        single-headed HH - extracted from demographic data of HH adult members
        Returns:

        """
        # TODO: Should we exclude eldery?
        now = datetime.datetime.now()
        criteria = [("birthdate", "<", now - relativedelta(years=CHILDREN_AGE_LIMIT))]
        for record in self:
            if record["is_group"]:
                cnt = record.count_individuals(kinds=None, criteria=criteria)
                record["z_crt_grp_is_single_head_hh"] = cnt > 0
            else:
                record["z_crt_grp_is_single_head_hh"] = None

    def _compute_crt_grp_is_woman_head_hh(self):
        """
        female-headed HH - extracted from demographic data of HH adult members
        Returns:

        """
        _logger.info("-" * 80)
        _logger.info("_compute_crt_grp_is_woman_head_hh")
        _logger.info("self: %s", self)
        now = datetime.datetime.now()
        criteria = [
            ("birthdate", "<", now - relativedelta(years=CHILDREN_AGE_LIMIT)),
            ("gender", "=", "Female"),
        ]
        for record in self:
            if record["is_group"]:
                cnt = record.count_individuals(kinds=["Head"], criteria=criteria)
                _logger.info(cnt)
                record["z_crt_grp_is_woman_head_hh"] = cnt > 0
            else:
                record["z_crt_grp_is_woman_head_hh"] = False

    def _compute_crt_grp_is_eldery_head_hh(self):
        """
        Elderly-headed HHs - extracted from demographic
        data of HH adult members
        Returns:

        """
        _logger.info("-" * 80)
        _logger.info("_compute_crt_grp_is_eldery_head_hh")
        _logger.info("self: %s", self)
        now = datetime.datetime.now()
        criteria = [("birthdate", "<", now - relativedelta(years=ELDERLY_AGE_LIMIT))]
        for record in self:
            if record["is_group"]:
                cnt = record.count_individuals(kinds=["Head"], criteria=criteria)
                _logger.info("cnt: %s", cnt)
                record.z_crt_grp_is_elderly_head_hh = cnt > 0
            else:
                record.z_crt_grp_is_elderly_head_hh = None

    def _compute_crt_grp_is_hh_with_children(self):
        """
        Households (HH) with children - extracted from demographic data of HH adult members
        plus child members from personal data
        """
        now = datetime.datetime.now()
        children = now - relativedelta(years=CHILDREN_AGE_LIMIT)
        criteria = [("birthdate", ">=", children)]
        for record in self:
            if record["is_group"]:
                cnt = record.count_individuals(kinds=None, criteria=criteria)
                record["z_crt_grp_is_hh_with_children"] = cnt > 0
            else:
                record["z_crt_grp_is_hh_with_children"] = None

    def _compute_crt_grp_is_hh_with_pregnant_lactating(self):
        """
        Households (HH) with pregnant and lactating
        """
        datetime.datetime.now()
        criteria = [
            "|",
            ("z_cst_ind_pregnancy_start", "!=", None),
            ("z_cst_ind_lactation_start", "=", None),
        ]
        for record in self:
            if record["is_group"]:
                cnt = record.count_individuals(kinds=None, criteria=criteria)
                record.z_crt_grp_is_hh_with_pregnant_lactating = cnt > 0
            else:
                record.z_crt_grp_is_hh_with_pregnant_lactating = None

    def _compute_crt_grp_is_hh_with_disabled(self):
        """
        HHs with disabled (mental or physical) members
        """
        criteria = [("z_cst_ind_disability_level", ">", 0)]
        for record in self:
            if record["is_group"]:
                cnt = record.count_individuals(kinds=None, criteria=criteria)
                record.z_crt_grp_is_hh_with_disabled = cnt > 0
            else:
                record.z_crt_grp_is_hh_with_disabled = None

    def _compute_crt_grp_is_hh_with_medical_condition(self):
        """
        HHs with members that have chronic illness/medical conditions
        """
        criteria = [("z_cst_ind_medical_condition", ">", 0)]
        for record in self:
            if record["is_group"]:
                cnt = record.count_individuals(kinds=None, criteria=criteria)
                record.z_crt_grp_is_hh_with_medical_condition = cnt > 0
            else:
                record.z_crt_grp_is_hh_with_medical_condition = None

    def _compute_crt_grp_is_hh_with_elderly(self):
        """
        Households (HH) with elderly - extracted from demographic data of HH adult members
        plus elderly members from personal data
        """
        now = datetime.datetime.now()
        criteria = [("birthdate", "<", now - relativedelta(years=ELDERLY_AGE_LIMIT))]
        for record in self:
            if record["is_group"]:
                cnt = record.count_individuals(kinds=None, criteria=criteria)
                record.z_crt_grp_is_hh_with_elderly = cnt > 0
            else:
                record.z_crt_grp_is_hh_with_elderly = None

    def _compute_count_and_set(self, field_name, kinds, criteria):
        for record in self:
            if record["is_group"]:
                record[field_name] = record.count_individuals(
                    kinds=kinds, criteria=criteria
                )
            else:
                record[field_name] = None
