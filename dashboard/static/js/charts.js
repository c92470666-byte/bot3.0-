/**
 * PolyBot - Utilidades de gráficas
 */

class ChartFactory {
    /**
     * Crea una gráfica de línea para equity curve
     */
    static createEquityChart(canvasId, data, initialCapital = 1000) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        const labels = data.map((d, i) => {
            if (d.timestamp) {
                return new Date(d.timestamp).toLocaleDateString('es', {
                    month: 'short', day: 'numeric'
                });
            }
            return i === 0 ? 'Inicio' : `#${i}`;
        });

        const values = data.map(d => d.equity);
        const context = ctx.getContext('2d');

        // Gradient
        const gradient = context.createLinearGradient(0, 0, 0, 300);
        const isPositive = (values[values.length - 1] || 0) >= (values[0] || 0);

        if (isPositive) {
            gradient.addColorStop(0, 'rgba(16, 185, 129, 0.3)');
            gradient.addColorStop(1, 'rgba(16, 185, 129, 0.0)');
        } else {
            gradient.addColorStop(0, 'rgba(239, 68, 68, 0.3)');
            gradient.addColorStop(1, 'rgba(239, 68, 68, 0.0)');
        }

        return new Chart(context, {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    label: 'Equity',
                    data: values,
                    borderColor: isPositive ? '#10b981' : '#ef4444',
                    backgroundColor: gradient,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: values.length > 30 ? 0 : 3,
                    pointHoverRadius: 5,
                    pointBackgroundColor: isPositive ? '#10b981' : '#ef4444',
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index',
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#1e293b',
                        titleColor: '#e2e8f0',
                        bodyColor: '#e2e8f0',
                        borderColor: '#334155',
                        borderWidth: 1,
                        padding: 12,
                        displayColors: false,
                        callbacks: {
                            label: ctx => {
                                const val = ctx.parsed.y;
                                const pnl = val - initialCapital;
                                const pct = ((val - initialCapital) / initialCapital * 100);
                                return [
                                    `Equity: $${val.toFixed(2)}`,
                                    `P&L: ${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)} (${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%)`
                                ];
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(71, 85, 105, 0.3)', drawBorder: false },
                        ticks: { color: '#94a3b8', maxTicksLimit: 10, font: { size: 11 } }
                    },
                    y: {
                        grid: { color: 'rgba(71, 85, 105, 0.3)', drawBorder: false },
                        ticks: {
                            color: '#94a3b8',
                            font: { size: 11 },
                            callback: val => '$' + val.toFixed(0)
                        }
                    }
                }
            }
        });
    }

    /**
     * Crea gráfica de dona para win/loss ratio
     */
    static createWinLossChart(canvasId, wins, losses) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        return new Chart(ctx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['Ganados', 'Perdidos'],
                datasets: [{
                    data: [wins || 0, losses || 0],
                    backgroundColor: ['#10b981', '#ef4444'],
                    borderColor: ['#059669', '#dc2626'],
                    borderWidth: 2,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#94a3b8', padding: 15, font: { size: 12 } }
                    }
                }
            }
        });
    }
  }
