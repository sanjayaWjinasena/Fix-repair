# -*- coding: utf-8 -*-
{
    'name': 'Jinasena : Module : Repair',
    'version': '17.0.1.0.300',
    'summary': 'Enhancements to the Customer Care - Repair helpdesk workflow',
    'author': 'Jinasena Agricultural Machinery (Pvt) Ltd.',
    'category': 'Helpdesk',
    'license': 'LGPL-3',
    # v299: added `repair` to depends — models/repair_order.py ports
    # x_studio_confirm_draft_quotation onto repair.order. Without this
    # dep the _inherit target isn't in the registry when Fix-repair
    # loads on a fresh install.
    'depends': ['base_setup', 'helpdesk', 'helpdesk_fsm', 'repair', 'sale', 'sale_stock', 'industry_fsm_sale', 'industry_fsm_stock', 'BugFix-Sales', 'studio_usermodel_migration'],
    'post_init_hook': 'post_init_hook',
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
    'data': [
        # v249: MUST load before security/ir.model.access.csv so the
        # 11 Studio-created model xmlids resolve when the ACL CSV is
        # processed. Fresh installs don't need this (Odoo auto-pins
        # newly-declared models) but existing Clear-DB upgrades do
        # (models pre-existed as state='manual' Studio rows, never
        # got a Fix-repair-owned ir.model.data pin auto-created).
        'data/ir_model_pins.xml',
        'security/ir.model.access.csv',
        'data/fix_repair_data.xml',
        'data/repair_stages.xml',
        'data/repair_sequences.xml',
        'data/helpdesk_ticket_types.xml',
        # v299: catalog views (form / tree / search + Studio inherit
        # tree) for the 7 diagnosis-catalogue models. MUST load
        # before repair_diagnosis_menus.xml so the actions that menu
        # file creates already have primary views available on fresh
        # install (Odoo would otherwise auto-generate a default tree
        # that lacks the Studio inherit's editable="bottom" +
        # Description / Area / Company extra columns).
        'views/repair_diagnosis_catalog_views.xml',
        'data/repair_diagnosis_menus.xml',
        'data/repair_diagnosis_seed.xml',
        # v253: expose RR - Auto Create Repair Route in the Actions
        # dropdown. Load after ACL CSV (server action has no ACL of
        # its own but keeps ordering consistent) and before view files.
        'data/helpdesk_ticket_server_actions.xml',
        # v265: expose RR - End Quick Repair (Tested OK button target)
        # as a Python-declared ir.actions.server. MUST load before
        # views/project_task_studio_ported.xml which references it via
        # %(Fix-repair.action_repair_end_quick_repair)d.
        'data/project_task_server_actions.xml',
        # v292: studio_ported.xml MUST load before helpdesk_ticket_views.xml.
        # studio_ported.xml adds ghost-field anchors (invisible x_studio_*
        # fields) so that helpdesk_ticket_studio_field_hides.xml xpaths can
        # resolve on DBs where the Studio view does not include those fields.
        # Without this ordering, the DB still holds the old ported view (no
        # ghost fields) when helpdesk_ticket_views.xml triggers full view
        # tree validation — causing a ParseError on the hide view's xpaths.
        'views/helpdesk_ticket_studio_ported.xml',
        'views/helpdesk_ticket_studio_field_hides.xml',
        'views/helpdesk_ticket_views.xml',
        'views/helpdesk_ticket_type_views.xml',
        # v259: Repair Diagnosis tab on project.task form
        'views/project_task_studio_ported.xml',
        # v267: Approve/Reject RUG direct-method buttons on sale.order
        'views/sale_order_studio_ported.xml',
        # v269: repair-movement field placements on stock.picking
        'views/stock_picking_studio_ported.xml',
        'views/res_config_settings_views.xml',
        'views/sale_report_templates.xml',
        'views/helpdesk_stage_studio_ported.xml',
        'views/helpdesk_team_studio_ported.xml',
        'views/helpdesk_ticket_type_studio_ported.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'Fix-repair/static/src/scss/task_toast_triggers.scss',
            'Fix-repair/static/src/js/task_missing_data_notifier.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}
