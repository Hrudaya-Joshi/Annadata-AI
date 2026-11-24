/**
 * ANNADATA AI — Geolocation Helper
 * Automatically handles browser GPS requests, reverse geocoding via /api/geo/reverse,
 * and populates address + internal hidden latitude/longitude fields.
 */
window.annadataGeo = {
    detectLocation: function(options) {
        const addrInputId = options.addressInputId || 'locationAddress';
        const latInputId  = options.latInputId || 'geoLat';
        const lngInputId  = options.lngInputId || 'geoLng';
        const statusElId  = options.statusId || 'geoStatus';
        const btnId       = options.buttonId || 'btnDetectLocation';

        const addrInput = document.getElementById(addrInputId);
        const latInput  = document.getElementById(latInputId);
        const lngInput  = document.getElementById(lngInputId);
        const statusEl  = document.getElementById(statusElId);
        const btn       = document.getElementById(btnId);

        if (!navigator.geolocation) {
            if (statusEl) {
                statusEl.innerHTML = '<span class="text-danger small"><i data-lucide="alert-circle" style="width:12px;height:12px;"></i> Geolocation is not supported by your browser. Please enter your address manually.</span>';
                if (window.lucide) window.lucide.createIcons();
            }
            return;
        }

        if (btn) {
            btn.classList.add('loading');
            btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status"></span> Detecting GPS Coordinates...';
        }
        if (statusEl) {
            statusEl.innerHTML = '<span class="text-muted small"><span class="spinner-border spinner-border-sm me-1"></span> Requesting GPS location permission from browser...</span>';
        }

        navigator.geolocation.getCurrentPosition(
            async (position) => {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;

                if (latInput) latInput.value = lat.toFixed(6);
                if (lngInput) lngInput.value = lon.toFixed(6);

                if (statusEl) {
                    statusEl.innerHTML = '<span class="text-muted small"><span class="spinner-border spinner-border-sm me-1"></span> GPS coordinates acquired (' + lat.toFixed(4) + '°, ' + lon.toFixed(4) + '°). Resolving human-readable address...</span>';
                }

                try {
                    const response = await fetch('/api/geo/reverse?lat=' + encodeURIComponent(lat) + '&lon=' + encodeURIComponent(lon));
                    const data = await response.json();

                    if (data && data.address) {
                        if (addrInput) addrInput.value = data.address;
                        if (statusEl) {
                            statusEl.innerHTML = '<span class="text-success small fw-semibold"><i data-lucide="check-circle-2" style="width:14px;height:14px;"></i> GPS Location detected: ' + data.address + '</span>';
                        }
                    } else {
                        if (addrInput && !addrInput.value) {
                            addrInput.value = 'Detected Coordinates: ' + lat.toFixed(4) + ', ' + lon.toFixed(4);
                        }
                        if (statusEl) {
                            statusEl.innerHTML = '<span class="text-success small"><i data-lucide="check-circle" style="width:14px;height:14px;"></i> Coordinates detected successfully (' + lat.toFixed(4) + ', ' + lon.toFixed(4) + ')</span>';
                        }
                    }
                } catch (err) {
                    console.warn('Reverse geocoding error:', err);
                    if (addrInput && !addrInput.value) {
                        addrInput.value = 'GPS Location: ' + lat.toFixed(4) + ', ' + lon.toFixed(4) + ', Bengaluru';
                    }
                    if (statusEl) {
                        statusEl.innerHTML = '<span class="text-success small"><i data-lucide="check-circle" style="width:14px;height:14px;"></i> GPS detected successfully. Coordinates saved internally.</span>';
                    }
                } finally {
                    if (btn) {
                        btn.classList.remove('loading');
                        btn.innerHTML = '<i data-lucide="refresh-cw" class="me-1" style="width:14px;height:14px;"></i> Refresh GPS Location';
                    }
                    if (window.lucide) window.lucide.createIcons();
                }
            },
            (error) => {
                let msg = 'Could not access GPS. Please type your location address manually.';
                if (error.code === error.PERMISSION_DENIED) {
                    msg = 'GPS permission was declined. You can type your location address manually below.';
                } else if (error.code === error.POSITION_UNAVAILABLE) {
                    msg = 'GPS location is temporarily unavailable. Please enter your address manually.';
                } else if (error.code === error.TIMEOUT) {
                    msg = 'GPS request timed out. Please enter your address manually.';
                }

                if (statusEl) {
                    statusEl.innerHTML = '<span class="text-terracotta small"><i data-lucide="map-pin-off" style="width:12px;height:12px;"></i> ' + msg + '</span>';
                }
                if (btn) {
                    btn.classList.remove('loading');
                    btn.innerHTML = '<i data-lucide="crosshair" class="me-1" style="width:14px;height:14px;"></i> Use My Current Location';
                }
                if (window.lucide) window.lucide.createIcons();
            },
            { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
        );
    }
};
