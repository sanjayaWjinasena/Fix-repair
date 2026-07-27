/** @odoo-module **/
/*
 * Fix-repair — task-form Add Data toast dispatcher (v208).
 *
 * Companion to project_task._get_view's fix_repair_task_toast_trigger
 * <div>s. Those divs live in the arch with an `invisible=...`
 * expression that mirrors the ORIGINAL Studio buttons' visibility
 * (v190 removed the buttons; v207 tried inline banners; user wants
 * toasts). The divs themselves are hidden by CSS
 * (task_toast_triggers.scss) — they're not for humans, they're for
 * this observer.
 *
 * Odoo's own arch reactivity puts the divs INTO the DOM when the
 * invisible expression is False (i.e. data is missing) and REMOVES
 * them when the expression is True (data is set). A MutationObserver
 * on document.body catches both events and syncs a sticky warning
 * notification per trigger.
 *
 * Why this works when v205/v206's onPatched / useEffect didn't:
 *   * Arch invisible is Odoo's built-in mechanism — it re-evaluates
 *     on every field change (including binary uploads) because Odoo
 *     hooks into every widget's write path, not just onchange.
 *   * We're not fighting that mechanism, we're piggy-backing on it.
 */
import { registry } from "@web/core/registry";

const TOAST_SPECS = [
    {
        className: "fix_repair_task_toast_trigger--diagnosis",
        title: "Add Data",
        message:
            "Repair Diagnosis Validation is not set for this task. "
            + "Please add the diagnosis.",
    },
    {
        className: "fix_repair_task_toast_trigger--image",
        title: "Add Data",
        message:
            "Repair Image is not set for this task. "
            + "Please upload the repair image.",
    },
];

const notifierService = {
    dependencies: ["notification"],
    start(env) {
        const notification = env.services.notification;
        // key = className, value = dismiss function from
        // notification.add({...sticky: true}).
        const activeToasts = {};

        function syncToasts() {
            for (const spec of TOAST_SPECS) {
                const trigger = document.querySelector(
                    "." + spec.className,
                );
                const present = !!trigger;
                const alreadyToasted = !!activeToasts[spec.className];
                if (present && !alreadyToasted) {
                    activeToasts[spec.className] = notification.add(
                        spec.message,
                        {
                            type: "warning",
                            title: spec.title,
                            sticky: true,
                        },
                    );
                } else if (!present && alreadyToasted) {
                    try {
                        activeToasts[spec.className]();
                    } catch (err) {
                        // Notification already gone — safe to ignore.
                    }
                    delete activeToasts[spec.className];
                }
            }
        }

        // Initial sync in case the form is already mounted with
        // triggers present at boot time (rare — usually the form
        // mounts after the service starts).
        syncToasts();

        // Watch every DOM mutation on the body. The trigger divs
        // are cheap to search for (single class lookup) so calling
        // syncToasts on every batch is fine.
        const obs = new MutationObserver(syncToasts);
        obs.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ["class", "style"],
        });
    },
};

registry
    .category("services")
    .add("fix_repair_task_missing_data_notifier", notifierService);
