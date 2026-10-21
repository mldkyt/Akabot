document.addEventListener("click", function (event) {
    const deleteButton = event.target.closest("[data-confirm-delete]");
    if (deleteButton) {
        const group = deleteButton.closest(".confirm-actions");
        const confirm = group ? group.querySelector(".confirm-inline") : null;
        if (confirm) {
            confirm.hidden = false;
            deleteButton.hidden = true;
        }
        return;
    }

    const cancelButton = event.target.closest("[data-confirm-cancel]");
    if (cancelButton) {
        const group = cancelButton.closest(".confirm-actions");
        const confirm = group ? group.querySelector(".confirm-inline") : null;
        const trigger = group ? group.querySelector("[data-confirm-delete]") : null;
        if (confirm) {
            confirm.hidden = true;
        }
        if (trigger) {
            trigger.hidden = false;
        }
        return;
    }

    const expandButton = event.target.closest("[data-expand-row]");
    if (expandButton) {
        const row = document.getElementById(expandButton.getAttribute("data-expand-row"));
        if (!row) {
            return;
        }

        const expanded = row.hidden;
        row.hidden = !expanded;
        expandButton.setAttribute("aria-expanded", String(expanded));
        expandButton.textContent = expanded ? "Close" : expandButton.dataset.collapsedLabel || "Edit";
    }
});
