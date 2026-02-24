document.addEventListener("DOMContentLoaded", function () {
    function updateTotalForRow(row) {
        const qtyInput = row.querySelector('[id$="item_qty"]');
        const amountInput = row.querySelector('[id$="item_amount"]');
        const totalField = row.querySelector('.field-total p');

        const qty = parseFloat(qtyInput?.value) || 0;
        const amount = parseFloat(amountInput?.value) || 0;
        const total = (qty * amount).toFixed(2);

        if (totalField) {
            totalField.textContent = total;
        }
    }

    function bindListeners(row) {
        const qtyInput = row.querySelector('[id$="item_qty"]');
        const amountInput = row.querySelector('[id$="item_amount"]');

        if (qtyInput) {
            qtyInput.addEventListener('input', () => updateTotalForRow(row));
        }

        if (amountInput) {
            amountInput.addEventListener('input', () => updateTotalForRow(row));
        }
    }

    // Bind to all current rows
    document.querySelectorAll('tr.dynamic-invoiceitem_set').forEach(row => {
        bindListeners(row);
        updateTotalForRow(row);
    });

    // Re-bind when new inline rows are added
    const formset = document.getElementById("invoiceitem_set-group");
    if (formset) {
        formset.addEventListener("click", function (e) {
            if (e.target.closest(".add-row")) {
                setTimeout(() => {
                    const rows = document.querySelectorAll('tr.dynamic-invoiceitem_set');
                    const lastRow = rows[rows.length - 1];
                    bindListeners(lastRow);
                    updateTotalForRow(lastRow);
                }, 100);
            }
        });
    }
});
