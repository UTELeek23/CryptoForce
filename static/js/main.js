// Main JavaScript file for CryptoForce

// Initialize tooltips and popovers
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Initialize Bootstrap popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'))
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl)
    });
});

// Function to initialize ELO history chart on profile page
function initEloChart(chartData) {
    if (!chartData || !document.getElementById('eloChart')) {
        return;
    }
    
    const ctx = document.getElementById('eloChart').getContext('2d');
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartData.timestamps,
            datasets: [{
                label: 'ELO Rating',
                data: chartData.elo_values,
                backgroundColor: 'rgba(78, 115, 223, 0.05)',
                borderColor: 'rgba(78, 115, 223, 1)',
                pointRadius: 3,
                pointBackgroundColor: 'rgba(78, 115, 223, 1)',
                pointBorderColor: 'rgba(78, 115, 223, 1)',
                pointHoverRadius: 5,
                pointHoverBackgroundColor: 'rgba(78, 115, 223, 1)',
                pointHoverBorderColor: 'rgba(78, 115, 223, 1)',
                pointHitRadius: 10,
                pointBorderWidth: 2,
                fill: true,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: {
                        display: false,
                        drawBorder: false
                    }
                },
                y: {
                    ticks: {
                        precision: 0
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: "rgb(255, 255, 255)",
                    bodyColor: "#858796",
                    titleMarginBottom: 10,
                    titleColor: '#6e707e',
                    titleFont: {
                        size: 14
                    },
                    borderColor: '#dddfeb',
                    borderWidth: 1,
                    padding: 15,
                    displayColors: false
                }
            }
        }
    });
}

// Contest countdown timer
function initCountdown(endTime, elementId) {
    const countdownElement = document.getElementById(elementId);
    if (!countdownElement) return;

    function updateCountdown() {
        const now = new Date().getTime();
        const distance = new Date(endTime).getTime() - now;
        
        if (distance <= 0) {
            countdownElement.innerHTML = "Contest has ended";
            return;
        }
        
        // Time calculations
        const days = Math.floor(distance / (1000 * 60 * 60 * 24));
        const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((distance % (1000 * 60)) / 1000);
        
        // Display the result
        countdownElement.innerHTML = `${days}d ${hours}h ${minutes}m ${seconds}s`;
    }
    
    // Update the countdown every 1 second
    updateCountdown();
    setInterval(updateCountdown, 1000);
}

// Flag submission form handler
function setupFlagSubmission() {
    const flagForm = document.getElementById('flag-submission-form');
    if (!flagForm) return;
    
    flagForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const flagInput = document.getElementById('flag-input');
        const problemId = flagForm.dataset.problemId;
        const submitButton = flagForm.querySelector('button[type="submit"]');
        const resultDiv = document.getElementById('submission-result');
        
        // Disable the button and show loading state
        submitButton.disabled = true;
        submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Submitting...';
        
        // This would be replaced with an actual fetch request to your submission endpoint
        setTimeout(() => {
            submitButton.disabled = false;
            submitButton.textContent = 'Submit Flag';
            
            // This is where you'd handle the response from your backend
            resultDiv.innerHTML = '<div class="alert alert-success">Flag submitted successfully!</div>';
            flagInput.value = '';
        }, 1500);
    });
}