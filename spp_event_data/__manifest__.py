# Part of OpenSPP. See LICENSE file for full copyright and licensing details.


{
    "name": "Event Data",
    "category": "OpenSPP",
    "version": "15.0.1.1.0",
    "sequence": 1,
    "author": "OpenSPP.org",
    "website": "https://github.com/openspp/openspp-modules",
    "license": "LGPL-3",
    "development_status": "Beta",
    "maintainers": ["jeremi", "gonzalesedwin1123", "emjay0921"],
    "depends": ["base", "g2p_registry_base", "g2p_registry_group"],
    "data": [
        "security/ir.model.access.csv",
        "views/event_data_view.xml",
        "views/registrant_view.xml",
        "wizard/create_event_wizard.xml",
    ],
    "assets": {},
    "demo": [],
    "images": [],
    "application": True,
    "installable": True,
    "auto_install": False,
}
