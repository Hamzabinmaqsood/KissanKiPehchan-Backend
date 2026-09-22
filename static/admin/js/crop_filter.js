document.addEventListener("DOMContentLoaded", function () {
    var seasonField = document.getElementById("id_season");
    const cropField = document.getElementById("id_crop");
    console.log(cropField)
    if (!seasonField) {
        seasonField = document.getElementById("id_crop_season");

    }
    if (!seasonField || !cropField) return;

    function clearAndTrigger() {
        // clear options
        cropField.innerHTML = "";

        // trigger Select2 refresh
        const event = new Event("change", { bubbles: true });
        cropField.dispatchEvent(event);
    }

    seasonField.addEventListener("change", function () {
        const seasonId = this.value;

        clearAndTrigger();

        if (!seasonId) return;

        fetch(`/api/cr/ajax/get-crops/?season_id=${seasonId}`)
            .then(res => res.json())
            .then(data => {

                // add empty option
                const emptyOption = new Option("---------", "");
                cropField.add(emptyOption);

                data.forEach(item => {
                    const option = new Option(item.name, item.id);
                    cropField.add(option);
                });

                // 🔥 IMPORTANT: notify Select2
                const event = new Event("change", { bubbles: true });
                cropField.dispatchEvent(event);
            });
    });
});