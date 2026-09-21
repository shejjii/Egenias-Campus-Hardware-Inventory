/* =========================================================
   CAMPUS HARDWARE INVENTORY
   SMALL BROWSER INTERACTIONS
   ========================================================= */


/* =========================================================
   DELETE CONFIRMATION
   ========================================================= */

function confirmDelete(itemName) {

    return confirm(
        "Are you sure you want to delete " +
        itemName +
        "?"
    );

}


/* =========================================================
   BORROW QUANTITY
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    const quantityInput =
        document.getElementById("quantity");

    if (quantityInput) {

        quantityInput.addEventListener("input", function () {

            const min =
                parseInt(quantityInput.min || "1");

            const max =
                parseInt(quantityInput.max || "999999");

            let value =
                parseInt(quantityInput.value);

            if (isNaN(value)) {
                return;
            }

            if (value < min) {
                quantityInput.value = min;
            }

            if (value > max) {
                quantityInput.value = max;
            }

        });

    }


    /* =====================================================
       PASSWORD CONFIRMATION
       ===================================================== */

    const passwordForm =
        document.querySelector(
            "[data-password-form='true']"
        );

    if (passwordForm) {

        passwordForm.addEventListener(
            "submit",
            function (event) {

                const newPassword =
                    document.getElementById(
                        "new_password"
                    ).value;

                const confirmPassword =
                    document.getElementById(
                        "confirm_password"
                    ).value;

                if (newPassword !== confirmPassword) {

                    event.preventDefault();

                    alert(
                        "The new passwords do not match."
                    );

                }

            }
        );

    }


    /* =====================================================
       SET MINIMUM DUE DATE
       ===================================================== */

    const dueDate =
        document.getElementById("due_date");

    if (dueDate) {

        const today =
            new Date().toISOString().split("T")[0];

        dueDate.min = today;

    }


    /* =====================================================
       AUTO HIDE FLASH MESSAGES
       ===================================================== */

    const flashes =
        document.querySelectorAll(".flash");

    flashes.forEach(function (flash) {

        setTimeout(function () {

            flash.style.transition =
                "opacity 0.3s ease";

            flash.style.opacity = "0";

            setTimeout(function () {
                flash.remove();
            }, 300);

        }, 5000);

    });

});