{
    "name": """OpenSPP REST API: API Records""",
    "summary": """RESTful API routes for OpenSPP""",
    "category": "",
    "version": "15.0.0.0.0",
    "author": "OpenSPP.org",
    "development_status": "Alpha",
    "website": "https://github.com/openspp/openspp-program",
    "license": "LGPL-3",
    "depends": [
        "base",
        "spp_api",
        "spp_service_points",
        "uom",
        "spp_service_point_device",
        "product",
        "g2p_programs",
        "spp_programs",
        "g2p_entitlement_cash",
        "spp_entitlement_in_kind",
        "spp_ent_trans",
        "contacts",
        "g2p_registry_base",
        "spp_area",
        "spp_programs_sp",
    ],
    "data": [
        "data/spp_api_namespace_data.xml",
        "data/spp_api_path_data.xml",
        "views/spp_service_point_views.xml",
        "views/uom_category_views.xml",
        "data/spp_api_field_data.xml",
        "data/spp_api_field_alias_data.xml",
    ],
    "application": False,
    "auto_install": False,
    "installable": True,
}