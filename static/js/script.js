document.addEventListener('DOMContentLoaded', function() {
    const locationSelect = document.getElementById('location-select');
    const fieldSelect = document.getElementById('field-select');
    const fieldInfo = document.getElementById('field-info');
    const fieldDetails = document.getElementById('field-details');
    const soilTestRadio = document.querySelectorAll('input[name="soil-test"]');
    const calculateBtn = document.getElementById('calculate-btn');
    const resultsSection = document.getElementById('results-section');
    
    // Load locations
    fetch('/api/locations')
        .then(response => response.json())
        .then(locations => {
            locations.forEach(location => {
                const option = document.createElement('option');
                option.value = location;
                option.textContent = location;
                locationSelect.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error loading locations:', error);
            alert('অঞ্চল লোড করতে সমস্যা হয়েছে। পৃষ্ঠাটি রিফ্রেশ করুন।');
        });
    
    // Handle location selection
    locationSelect.addEventListener('change', function() {
        const location = this.value;
        if (location) {
            fetch(`/api/fields/${encodeURIComponent(location)}`)
                .then(response => response.json())
                .then(fields => {
                    fieldSelect.innerHTML = '<option value="">-- জমি নং নির্বাচন করুন --</option>';
                    fields.forEach(field => {
                        const option = document.createElement('option');
                        option.value = field.field_id;
                        option.textContent = `জমি নং ${field.field_id}`;
                        option.setAttribute('data-seasons', JSON.stringify(field.seasons));
                        fieldSelect.appendChild(option);
                    });
                    
                    document.getElementById('field-section').style.display = 'block';
                })
                .catch(error => {
                    console.error('Error loading fields:', error);
                    alert('জমির তথ্য লোড করতে সমস্যা হয়েছে।');
                });
        }
    });
    
    // Handle field selection
    fieldSelect.addEventListener('change', function() {
        if (this.value) {
            const selectedOption = this.options[this.selectedIndex];
            const seasons = JSON.parse(selectedOption.getAttribute('data-seasons'));
            
            // Display field information
            let infoHtml = '';
            if (seasons['বছর ব্যাপী']) {
                const seasonData = seasons['বছর ব্যাপী'];
                if (seasonData.is_combined) {
                    // Special handling for field 13 with combined crops
                    const yields = seasonData.yield_target.split('এবং');
                    const crops = seasonData.crop.split('এবং');
                    infoHtml = `<p><strong>বছরব্যাপী ফসল:</strong> ${crops[0].trim()} এবং ${crops[1].trim()}</p>`;
                    infoHtml += `<p><strong>লক্ষ্যমাত্রা ফলন:</strong> ${yields[0].trim()} কেজি/শতাংশ (${crops[0].trim()}) এবং ${yields[1].trim()} কেজি/শতাংশ (${crops[1].trim()})</p>`;
                } else {
                    infoHtml = `<p><strong>বছরব্যাপী ফসল:</strong> ${seasonData.crop}</p>`;
                    infoHtml += `<p><strong>লক্ষ্যমাত্রা ফলন:</strong> ${seasonData.yield_target} কেজি/শতাংশ</p>`;
                }
            } else {
                if (seasons['রবি']) {
                    infoHtml += `<p><strong>রবি মৌসুম:</strong> ${seasons['রবি'].crop} (লক্ষ্য: ${seasons['রবি'].yield_target} কেজি/শতাংশ)</p>`;
                }
                if (seasons['খরিফ-১']) {
                    infoHtml += `<p><strong>খরিফ-১ মৌসুম:</strong> ${seasons['খরিফ-১'].crop} (লক্ষ্য: ${seasons['খরিফ-১'].yield_target} কেজি/শতাংশ)</p>`;
                }
                if (seasons['খরিফ-২']) {
                    infoHtml += `<p><strong>খরিফ-২ মৌসুম:</strong> ${seasons['খরিফ-২'].crop} (লক্ষ্য: ${seasons['খরিফ-২'].yield_target} কেজি/শতাংশ)</p>`;
                }
            }
            
            fieldDetails.innerHTML = infoHtml;
            fieldInfo.style.display = 'block';
            document.getElementById('details-section').style.display = 'block';
        } else {
            fieldInfo.style.display = 'none';
            document.getElementById('details-section').style.display = 'none';
        }
    });
    
    // Toggle soil test fields
    soilTestRadio.forEach(radio => {
        radio.addEventListener('change', function() {
            document.getElementById('soil-test-fields').style.display = 
                this.value === 'yes' ? 'block' : 'none';
        });
    });
    
    // Calculate recommendations
    calculateBtn.addEventListener('click', function() {
        const location = locationSelect.value;
        const fieldId = parseInt(fieldSelect.value);
        const landArea = parseFloat(document.getElementById('land-area').value) || 1;
        const hasSoilTest = document.querySelector('input[name="soil-test"]:checked').value === 'yes';
        const useDap = document.querySelector('input[name="use-dap"]:checked').value === 'yes';
        
        // Validate inputs
        if (!location || !fieldId) {
            alert('দয়া করে অঞ্চল এবং জমি নং নির্বাচন করুন।');
            return;
        }
        
        if (landArea <= 0) {
            alert('জমির পরিমাণ অবশ্যই ০ এর বেশি হতে হবে।');
            return;
        }
        
        const requestData = {
            location: location,
            field_id: fieldId,
            land_area: landArea,
            use_dap: useDap
        };
        
        if (hasSoilTest) {
            requestData.soil_test = {
                nitrogen: parseFloat(document.getElementById('nitrogen').value) || 0.10,
                phosphorus: parseFloat(document.getElementById('phosphorus').value) || 20.00,
                potassium: parseFloat(document.getElementById('potassium').value) || 0.15,
                magnesium: parseFloat(document.getElementById('magnesium').value) || 0.80,
                sulfur: parseFloat(document.getElementById('sulfur').value) || 15.00,
                zinc: parseFloat(document.getElementById('zinc').value) || 1.20,
                boron: parseFloat(document.getElementById('boron').value) || 0.21
            };
        }
        
        // Show loading state
        calculateBtn.disabled = true;
        calculateBtn.textContent = 'গণনা করা হচ্ছে...';
        
        fetch('/api/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('সার্ভারে সমস্যা হয়েছে।');
            }
            return response.json();
        })
        .then(recommendations => {
            displayResults(recommendations);
            resultsSection.style.display = 'block';
            
            // Scroll to results
            resultsSection.scrollIntoView({ behavior: 'smooth' });
        })
        .catch(error => {
            console.error('Error:', error);
            alert('সুপারিশ গণনা করতে সমস্যা হয়েছে: ' + error.message);
        })
        .finally(() => {
            // Reset button state
            calculateBtn.disabled = false;
            calculateBtn.textContent = 'সুপারিশ দেখুন';
        });
    });
    
    // Display results
    function displayResults(recommendations) {
        const resultsDiv = document.getElementById('recommendations');
        resultsDiv.innerHTML = '';
        
        if (Object.keys(recommendations).length === 0) {
            resultsDiv.innerHTML = '<p>কোন সুপারিশ পাওয়া যায়নি। দয়া করে অন্য জমি নং নির্বাচন করুন。</p>';
            return;
        }
        
        for (const [season, data] of Object.entries(recommendations)) {
            const seasonDiv = document.createElement('div');
            seasonDiv.className = 'season-result';
            
            if (data.fallow) {
                seasonDiv.innerHTML = `
                    <h3>${season} মৌসুম</h3>
                    <p>জমি পতিত থাকবে, কোন সারের প্রয়োজন নেই</p>
                `;
            } else {
                let fertilizerHtml = '<table class="fertilizer-table"><tr><th>সারের নাম</th><th>পরিমাণ</th></tr>';
                
                // Display all fertilizers
                const fertilizers = [
                    {key: 'urea', name: 'ইউরিয়া', unit: 'গ্রাম'},
                    {key: 'tsp', name: 'টিএসপি', unit: 'গ্রাম'},
                    {key: 'dap', name: 'ডিএপি', unit: 'গ্রাম'},
                    {key: 'mop', name: 'এমওপি', unit: 'গ্রাম'},
                    {key: 'gypsum', name: 'জিপসাম', unit: 'গ্রাম'},
                    {key: 'magnesium_sulfate', name: 'ম্যাগনেসিয়াম সালফেট', unit: 'গ্রাম'},
                    {key: 'zinc_sulfate', name: 'জিঙ্ক সালফেট', unit: 'গ্রাম'},
                    {key: 'boric_acid', name: 'বোরিক এসিড', unit: 'গ্রাম'}
                ];
                
                for (const fert of fertilizers) {
                    if (data[fert.key] > 0) {
                        fertilizerHtml += `
                            <tr>
                                <td>${fert.name}</td>
                                <td>${data[fert.key].toFixed(2)} ${fert.unit}</td>
                            </tr>
                        `;
                    }
                }
                
                if (data.organic_manure > 0) {
                    fertilizerHtml += `
                        <tr>
                            <td>জৈবসার</td>
                            <td>${data.organic_manure.toFixed(2)} কেজি</td>
                        </tr>
                    `;
                }
                
                fertilizerHtml += '</table>';
                
                // Handle combined yield targets for field 13
                let yieldDisplay;
                if (data.is_combined) {
                    const yields = data.yield_target.split('এবং');
                    const crops = data.crop.split('এবং');
                    yieldDisplay = `${yields[0].trim()} কেজি/শতাংশ (${crops[0].trim()}) এবং ${yields[1].trim()} কেজি/শতাংশ (${crops[1].trim()})`;
                } else {
                    yieldDisplay = `${data.yield_target} কেজি/শতাংশ`;
                }
                
                seasonDiv.innerHTML = `
                    <h3>${season} মৌসুম - ${data.crop}</h3>
                    <p><strong>লক্ষ্যমাত্রা ফলন:</strong> ${yieldDisplay}</p>
                    <h4>সার সুপারিশ:</h4>
                    ${fertilizerHtml}
                `;
            }
            
            resultsDiv.appendChild(seasonDiv);
        }
    }
});