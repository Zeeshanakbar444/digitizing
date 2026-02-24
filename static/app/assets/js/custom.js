    function toggleEditRemarks() {
        const status = document.getElementById("id_order_status").value;
        const remarksField = document.querySelector(".field-edit_remarks");

        if (status === "Edited") {
            remarksField.style.display = "block";
        } else {
            remarksField.style.display = "none";
        }
    }

    // Run on page load
    document.addEventListener("DOMContentLoaded", function () {
        toggleEditRemarks(); // Initial check
        document.getElementById("id_order_status").addEventListener("change", toggleEditRemarks);
    });

    function toggleUnit() {
        const status = document.getElementById("id_color_separation").value;
        const remarksField = document.querySelector(".form-row.field-unit.field-width.field-height");

        if (status === "Yes") {
            remarksField.style.display = "flex";
        } else {
            remarksField.style.display = "none";
        }
    }

    // Run on page load
    document.addEventListener("DOMContentLoaded", function () {
        toggleUnit(); // Initial check
        document.getElementById("id_color_separation").addEventListener("change", toggleUnit);
    });

    