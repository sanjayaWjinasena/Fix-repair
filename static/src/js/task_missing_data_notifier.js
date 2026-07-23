/** @odoo-module **/
/*
 * Fix-repair — repair-task missing-data toast notifier.
 *
 * Replaces the two Studio buttons "View Repair Diagnosis
 * Validation" and "View Repair Image Validation" that used to sit
 * on the task form header. Those buttons were only visible when
 * the corresponding data was missing — clicking them navigated to
 * a separate action to fill it in. The buttons cluttered the
 * form and forced a navigate-away step.
 *
 * v190: buttons removed from the sanitized task-form arch (see
 * helpdesk_ticket._sanitize_studio_task_form). Instead, on every
 * task form load, if the task is a repair task
 * (helpdesk_ticket_id set) AND the diagnosis / image data is
 * still empty, dispatch a sticky warning notification. The
 * notification stays until the salesperson dismisses it or
 * populates the missing data (the notification is dismissed
 * programmatically once the field flips to a set value).
 */
import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillUnmount } from "@odoo/owl";

patch(FormController.prototype, {
    setup() {
        super.setup();
        // Bail early on non-project.task forms — no cost for
        // sale.order / helpdesk.ticket / etc. renders.
        if (this.props.resModel !== "project.task") {
            return;
        }
        this.fixRepairNotification = useService("notification");
        this._fixRepairMissingDismissers = {};

        onMounted(() => this._fixRepairCheckMissingData());
        onWillUnmount(() => this._fixRepairClearMissingNotifications());
    },

    async onRecordSaved(record) {
        const result = await super.onRecordSaved(record);
        if (this.props.resModel === "project.task") {
            this._fixRepairCheckMissingData();
        }
        return result;
    },

    _fixRepairCheckMissingData() {
        const record = this.model?.root;
        if (!record || !record.data) return;
        const data = record.data;
        // Only fire for repair tasks — plain project.task records
        // outside the repair chain don't have helpdesk_ticket_id
        // and shouldn't see repair-workflow warnings.
        if (!data.helpdesk_ticket_id) {
            this._fixRepairClearMissingNotifications();
            return;
        }
        this._fixRepairSyncNotification(
            "diagnosis",
            !data.x_studio_valid_diagnosis,
            "Add Data",
            "Repair Diagnosis Validation is not set for this task. Please add the diagnosis.",
        );
        this._fixRepairSyncNotification(
            "image",
            !data.x_studio_repair_image_01,
            "Add Data",
            "Repair Image is not set for this task. Please upload the repair image.",
        );
    },

    _fixRepairSyncNotification(key, shouldShow, title, message) {
        const dismiss = this._fixRepairMissingDismissers[key];
        if (shouldShow && !dismiss) {
            this._fixRepairMissingDismissers[key] =
                this.fixRepairNotification.add(message, {
                    type: "warning",
                    title,
                    sticky: true,
                });
        } else if (!shouldShow && dismiss) {
            dismiss();
            delete this._fixRepairMissingDismissers[key];
        }
    },

    _fixRepairClearMissingNotifications() {
        if (!this._fixRepairMissingDismissers) return;
        for (const key of Object.keys(this._fixRepairMissingDismissers)) {
            try {
                this._fixRepairMissingDismissers[key]();
            } catch (err) {
                // Notification already gone — safe to ignore.
            }
        }
        this._fixRepairMissingDismissers = {};
    },
});
