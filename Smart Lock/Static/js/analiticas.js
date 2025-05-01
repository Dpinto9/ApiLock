// analytics.js
// ------------------------------ //
// Função para atualizar os dados das métricas e gráficos
// Configuração inicial do gráfico de linha
window.lineChartConfig = {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Acessos por Dia',
            data: [],
            borderColor: '#3498db',
            tension: 0.1,
            fill: false
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            y: {
                beginAtZero: true,
                ticks: {
                    stepSize: 1
                }
            }
        }
    }
};

function atualizarDados() {
    fetch('/analitica/dados')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log('Received data:', data); // Debug log

            // Update metrics and charts
            document.getElementById('totalAcessos').textContent = data.total_acessos;
            document.getElementById('taxaSucesso').textContent = data.taxa_sucesso + '%';
            document.getElementById('horarioPico').textContent = data.horario_pico;
            document.getElementById('tentativasNegadas').textContent = data.tentativas_negadas;

            // Update charts
            window.lineChart.data.labels = data.dias;
            window.lineChart.data.datasets[0].data = data.acessos_por_dia;
            window.lineChart.update();

            window.pieChart.data.datasets[0].data = data.tipos_acesso;
            window.pieChart.update();

            // Update recent access table with correct ID
            const tbody = document.getElementById('tabelaUltimosAcessos');
            if (tbody && data.ultimos_acessos) {
                tbody.innerHTML = '';
                data.ultimos_acessos.forEach(acesso => { 
                    const statusClass = acesso.status === 'autorizado' ? 'bg-success' : 'bg-danger';
                    tbody.innerHTML += `
                        <tr>
                            <td>${acesso.data}</td>
                            <td>${acesso.tipo}</td>
                            <td>
                                <span class="badge ${statusClass}">
                                    ${acesso.status}
                                </span>
                            </td>
                            <td>${acesso.metodo}</td>
                        </tr>
                    `;
                });
            }
        })
        .catch(error => {
            console.error('Erro ao atualizar dados:', error);
        });
}

document.addEventListener('DOMContentLoaded', function() {
    // Configuração do gráfico de linha
    const ctxLine = document.getElementById('acessosPorDia').getContext('2d');
    window.lineChart = new Chart(ctxLine, window.lineChartConfig);

    // Configuração do gráfico de pizza
    const ctxPie = document.getElementById('tiposAcesso').getContext('2d');
    window.pieChart = new Chart(ctxPie, {
        type: 'pie',
        data: {
            labels: ['PIN', 'QR Code', 'Outros'],
            datasets: [{
                data: [0, 0, 0], // Initial empty data
                backgroundColor: ['#2ecc71', '#3498db', '#95a5a6'],
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom',
                    labels: {
                        font: {
                            family: "'Helvetica Neue', 'Helvetica', 'Arial', sans-serif",
                            size: 12
                        },
                        padding: 20
                    }
                }
            }
        }
    });

    // Initial data load and set interval
    atualizarDados();
    setInterval(atualizarDados, 10000);
});