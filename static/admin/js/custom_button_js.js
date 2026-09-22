document.addEventListener('DOMContentLoaded', function () {

    console.log('Field Mapper JS connected');

    const targetField = document.getElementById('id_bbox');
    if (!targetField) return;

    const button = document.createElement('button');
    button.id = 'custom-button';
    button.className = 'custom-button';
    button.textContent = '📍 Mark Field on Map';

    button.style.backgroundColor = '#17c1e8';
    button.style.color = 'white';
    button.style.border = 'none';
    button.style.borderRadius = '5px';
    button.style.marginLeft = '10px';

    targetField.insertAdjacentElement('afterend', button);

    button.addEventListener('click', function (event) {
        event.preventDefault();

        const mapWindow = window.open('/api/mark-kml/', '_blank', 'width=900,height=650');

        const pollTimer = setInterval(function () {
            if (!mapWindow || mapWindow.closed) {
                clearInterval(pollTimer);

                const raw = localStorage.getItem('form_data');
                if (!raw) return;

                try {
                    const formData = JSON.parse(raw);
                    const coordinates = formData.coordinates || [];

                    if (!coordinates.length) {
                        console.warn('No coordinates found');
                        return;
                    }

                    const coordArray = coordinates.map(c => [c.lat, c.lng]);
                    targetField.value = JSON.stringify(coordArray);

                    console.log('bbox set with', coordinates.length, 'points');
                } catch (e) {
                    console.error('Parse error:', e);
                } finally {
                    localStorage.removeItem('form_data');
                }
            }
        }, 500);
    });
});