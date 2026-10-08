# -*- coding: utf-8 -*-
"""Hide fields/buttons of apps Jinasena doesn't use on the product and contact forms.

Replaces views/product_template_hide_dev_extras.xml and
views/res_partner_hide_dev_extras.xml (v368). Those views used one hard
<xpath> per element; when an app providing an element is not installed
(or gets uninstalled) the xpath cannot be located and Odoo refuses to
render the whole form ("Element ... cannot be located in parent view").

Here the same elements are hidden in _get_view, only if they are present,
so the forms open whatever apps are installed. Each target lists how many
occurrences the old view hid (first match, or first two where it used
[1]/[2] positional xpaths) to keep the exact same result.
"""
from odoo import models


def hide_present(env, arch, view, view_xmlid, targets):
    """Set invisible="1" on the targets found in ``arch`` when ``view`` is ``view_xmlid``.

    targets: iterable of (tag, name, occurrences). For action buttons the name
    may be a record name (``module.xmlid``); it also matches the numeric id
    Odoo stores for ``%(module.xmlid)d`` references.
    """
    target_view = env.ref(view_xmlid, raise_if_not_found=False)
    if not target_view or view != target_view:
        return
    for tag, name, occurrences in targets:
        names = {name}
        if '.' in name:
            action = env.ref(name, raise_if_not_found=False)
            if action:
                names.add(str(action.id))
        nodes = [n for n in arch.iter(tag) if n.get('name') in names]
        for node in nodes[:occurrences]:
            node.set('invisible', '1')


PRODUCT_TEMPLATE_EXTRAS = [
    # whole tabs
    ('page', 'ebay_sale', 1), ('page', 'pricing', 1),
    # eBay header buttons
    ('button', 'push_product_ebay', 1), ('button', 'relist_product_ebay', 1),
    ('button', 'revise_product_ebay', 1), ('button', 'end_listing_product_ebay', 1),
    # smart buttons of apps not used
    ('button', 'action_view_rentals', 1), ('button', 'action_view_offers', 1),
    ('button', 'action_view_storage_category_capacity', 1),
    # individual fields
    ('field', 'base_unit_count', 1), ('field', 'base_unit_id', 1), ('field', 'base_unit_name', 1),
    ('field', 'base_unit_price', 1), ('field', 'avatax_category_id', 1),
    ('field', 'description_self_order', 1), ('field', 'tic_category_id', 1),
    ('field', 'compare_list_price', 2), ('field', 'email_template_id', 1),
    ('field', 'intrastat_origin_country_id', 1), ('field', 'intrastat_supplementary_unit', 1),
    ('field', 'intrastat_supplementary_unit_amount', 1), ('field', 'optional_product_ids', 1),
    ('field', 'pricer_store_id', 1), ('field', 'pricer_tag_ids', 1), ('field', 'unspsc_code_id', 1),
    ('field', 'intrastat_code_id', 2), ('field', 'product_add_mode', 2), ('field', 'rent_ok', 2),
]

RES_PARTNER_EXTRAS = [
    ('page', 'membership', 1),
    ('group', 'group_partner_activation_review', 1),
    ('button', 'action_event_view', 1),
    ('button', 'action_view_certifications', 2),
    ('button', 'account_sepa_direct_debit.account_sepa_direct_debit_partner_mandates', 1),
    ('field', 'account_peppol_verification_label', 2), ('field', 'account_sepa_lei', 1),
    ('field', 'avatax_unique_code', 1), ('field', 'avalara_partner_code', 1),
    ('field', 'avalara_exemption_id', 1), ('field', 'box_1099_id', 1),
    ('field', 'citizen_identification', 1), ('field', 'ebay_id', 1),
    ('field', 'global_location_number', 2), ('field', 'website_tag_ids', 1),
    ('field', 'city_id', 2), ('field', 'vies_valid', 1),
    ('field', 'property_ups_carrier_account', 2),
]


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            hide_present(self.env, arch, view, 'product.product_template_only_form_view',
                         PRODUCT_TEMPLATE_EXTRAS)
        return arch, view


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            hide_present(self.env, arch, view, 'base.view_partner_form', RES_PARTNER_EXTRAS)
        return arch, view
