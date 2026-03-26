/**
 * PolyBot - JavaScript para página de configuración
 * Validaciones y UX del formulario
 */

document.addEventListener('DOMContentLoaded', () => {
    initConfigPage();
});

function initConfigPage() {
    // Inicializar tooltips
    initTooltips();

    // Inicializar validación en tiempo real
    initLiveValidation();

    // Inicializar toggle de campos Telegram
    initTelegramToggle();

    // Inicializar sliders visuales
    initRangeDisplays();
}

// ==========================================
// LIVE VALIDATION
// ==========================================
function initLiveValidation() {
    const numericInputs = document.querySelectorAll('input[type="number"]');

    numericInputs.forEach(input => {
        input.addEventListener('input', () => {
            const min = parseFloat(input.min);
            const max = parseFloat(input.max);
            const val = parseFloat(input.value);

            input.classList.remove('border-red-500', 'border-green-500');

            if (isNaN(val)) {
                input.classList.add('border-red-500');
                return;
            }

            if ((min !== undefined && val < min) || (max !== undefined && val > max)) {
                input.classList.add('border-red-500');
            } else {
                input.classList.add('border-green-500');
                setTimeout(() => input.classList.remove('border-green-500'), 1000);
            }
        });
    });
}

// ==========================================
// TELEGRAM TOGGLE
// ==========================================
function initTelegramToggle() {
    const toggle = document.querySelector('[name="telegram_enabled"]');
    const fields = document.getElementById('telegram-fields');

    if (!toggle || !fields) return;

    function updateVisibility() {
        if (toggle.checked) {
            fields.style.opacity = '1';
            fields.style.pointerEvents = 'auto';
        } else {
            fields.style.opacity = '0.4';
            fields.style.pointerEvents = 'none';
        }
    }

    toggle.addEventListener('change', updateVisibility);
    updateVisibility();
}

// ==========================================
// RANGE DISPLAYS
// ==========================================
function initRangeDisplays() {
    // Mostrar valor actual junto a inputs numéricos de riesgo
    const riskInputs = document.querySelectorAll('[name^="risk_"]');

    riskInputs.forEach(input => {
        input.addEventListener('input', () => {
            const display = input.parentElement.querySelector('.range-value');
            if (display) {
                display.textContent = input.value;
            }
        });
    });
}

// ==========================================
// TOOLTIPS
// ==========================================
function initTooltips() {
    // Los tooltips se manejan con CSS via data-tooltip attribute
}

// ==========================================
// SAVE WITH AJAX (alternativa al form submit)
// ==========================================
async function saveConfigAjax() {
    const form = document.getElementById('config-form');
    const formData = new FormData(form);

    // Convertir FormData a objeto
    const data = {};
    formData.forEach((value, key) => {
        if (data[key]) {
            if (!Array.isArray(data[key])) {
                data[key] = [data[key]];
            }
            data[key].push(value);
        } else {
            data[key] = value;
        }
    });

    try {
        const resp = await fetch('/config/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });

        const result = await resp.json();

        if (result.success) {
            Toast.success('✅ Configuración guardada correctamente');
        } else {
            const errors = result.errors || ['Error desconocido'];
            Toast.error('❌ ' + errors.join(', '));
        }
    } catch (e) {
        Toast.error('❌ Error de conexión');
    }
}

// ==========================================
// CAPITAL CALCULATOR
// ==========================================
function calculateRiskAmounts() {
    const capital = parseFloat(document.querySelector('[name="capital_initial"]')?.value || 0);
    const maxPos = parseFloat(document.querySelector('[name="risk_max_position"]')?.value || 0);
    const maxExp = parseFloat(document.querySelector('[name="risk_max_exposure"]')?.value || 0);
    const stopLoss = parseFloat(document.querySelector('[name="risk_stop_loss"]')?.value || 0);

    if (capital > 0) {
        const maxPosAmount = capital * (maxPos / 100);
        const maxExpAmount = capital * (maxExp / 100);
        const maxLossPerTrade = maxPosAmount * (stopLoss / 100);

        console.log(`Capital: $${capital}`);
        console.log(`Max por posición: $${maxPosAmount.toFixed(2)} (${maxPos}%)`);
        console.log(`Max exposición: $${maxExpAmount.toFixed(2)} (${maxExp}%)`);
        console.log(`Max pérdida por trade: $${maxLossPerTrade.toFixed(2)}`);
    }
      }
