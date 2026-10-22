{
    # upgrade-testing branch: data files below are commented out - this branch installs functions only, no data is seeded.
    "name": "Jinasena : Module : Repair",
    "version": "17.0.1.0.368",
    "summary": "Enhancements to the Customer Care - Repair helpdesk workflow",
    "author": "Jinasena Agricultural Machinery (Pvt) Ltd.",
    "category": "Helpdesk",
    "license": "LGPL-3",
    # v299: added `repair` to depends — models/repair_order.py ports
    # x_studio_confirm_draft_quotation onto repair.order. Without this
    # dep the _inherit target isn't in the registry when Fix-repair
    # loads on a fresh install.
    "depends": [
        "base_setup",
        "helpdesk",
        "helpdesk_fsm",
        "repair",
        "sale",
        "sale_stock",
        "industry_fsm_sale",
        "industry_fsm_stock",
        "industry_fsm_report",
        "BugFix-Sales",
        "studio_usermodel_migration",
    ],
    "post_init_hook": "post_init_hook",
    # v292: added studio_usermodel_migration to depends.
    # helpdesk_ticket.py declares related fields (x_studio_source_location,
    # x_studio_virtual_location, etc.) that traverse user_id -> res.users.
    # Those res.users fields were moved from Fix-repair's own res_users.py
    # to studio_usermodel_migration in v0.0.7 of that module, but the
    # manifest dep was never updated. Without this dep, Odoo's topological
    # loader may process Fix-repair before studio_usermodel_migration,
    # causing setup_related() to fail with KeyError on those fields.
    # Load order is now:
    #   BugFix-Sales -> studio_migrations -> studio_usermodel_migration
    #     -> Fix-repair -> Fix-Repair-Wizard-Nav
    # v244: helpdesk_ticket_studio_ported.xml + _studio_field_hides.xml
    # moved BACK to manifest 'data' now that the button-195 xpath was
    # stripped in v242. Loading via post_init_hook worked once but the
    # created ir.model.data records got purged on the NEXT upgrade by
    # Odoo's module cleanup (records not in manifest 'data' are treated
    # as orphans). Manifest data path keeps them tracked across upgrades.
    # ORDER: ported.xml before field_hides.xml — the latter's xpaths
    # target fields that ported.xml adds to the composed arch.
    "data": [
        "security/removed_handmade_access_rights.xml",
        "data/ir_model_data.xml",
        "security/fix_repair_security.xml",
        "security/ir.model.access.csv",
        "data/helpdesk_ticket_data.xml",
        "data/repair_order_data.xml",
        "data/x_conditions_data.xml",
        "data/x_diagnosis_areas_data.xml",
        "data/x_diagnosis_codes_data.xml",
        "data/x_resolutions_data.xml",
        "data/x_symptom_areas_data.xml",
        "data/x_symptom_codes_data.xml",
        "data/account_move_line_data.xml",
        "data/helpdesk_stage_data.xml",
        "data/helpdesk_ticket_type_data.xml",
        "data/project_task_data.xml",
        "data/res_users_data.xml",
        "data/sale_order_data.xml",
        "data/stock_picking_data.xml",
        "data/x_repair_master_data_migration_data.xml",
        "data/x_repair_accounts_data.xml",
        "data/x_repair_reason_custom_data.xml",
        "data/x_repair_reason_data.xml",
        "data/x_repair_stages_data.xml",
        "data/x_repair_sub_reason_data.xml",
        "data/x_task_diagnosis_data.xml",
        "views/helpdesk_ticket_views.xml",
        "views/repair_order_views.xml",
        "views/x_conditions_views.xml",
        "views/x_diagnosis_areas_views.xml",
        "views/x_diagnosis_codes_views.xml",
        "views/x_resolutions_views.xml",
        "views/x_symptom_areas_views.xml",
        "views/x_symptom_codes_views.xml",
        "views/x_task_diagnosis_views.xml",
        "views/x_repair_reason_custom_views.xml",
        "views/x_repair_reason_views.xml",
        "views/x_repair_stages_views.xml",
        "views/x_repair_sub_reason_views.xml",
        "views/helpdesk_team_views.xml",
        "views/helpdesk_ticket_type_views.xml",
        "views/project_task_views.xml",
        "views/sale_order_views.xml",
        "views/stock_picking_views.xml",
        "views/res_config_settings_views.xml",
        "views/helpdesk_ticket_report_analysis_views.xml",
        "views/x_repair_accounts_views.xml",
        "views/stock_warehouse_views.xml",
        "views/helpdesk_stage_views.xml",
        "views/res_users_views.xml",
        "views/res_partner_views.xml",
        "views/fix_repair_templates.xml",
        "views/fix_repair_menus.xml",
        # Not loaded on this branch:
        # 'data/repair_stages.xml',  # upgrade-testing: data, not shipped
        # 'data/repair_sequences.xml',  # upgrade-testing: data, not shipped
        # 'data/helpdesk_ticket_types.xml',  # upgrade-testing: data, not shipped
        # 'data/repair_diagnosis_seed.xml',  # upgrade-testing: data, not shipped
        # 'views/res_partner_hide_dev_extras.xml',
        # 'views/product_template_hide_dev_extras.xml',
    ],
    "assets": {
        "web.assets_backend": [
            "Fix-repair/static/src/scss/task_toast_triggers.scss",
            "Fix-repair/static/src/js/task_missing_data_notifier.js",
        ],
    },
}
