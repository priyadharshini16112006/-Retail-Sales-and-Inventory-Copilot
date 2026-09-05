document.addEventListener('DOMContentLoaded', () => {
    
    // Set Date
    const dateOptions = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    document.getElementById('currentDate').textContent = new Date().toLocaleDateString('en-IN', dateOptions);

    // Fetch logged-in user
    fetch('/api/me')
        .then(res => {
            if (res.status === 401) { window.location.href = '/login'; return null; }
            return res.json();
        })
        .then(user => {
            if (user) {
                const nameEl = document.getElementById('userFullName');
                if (nameEl) nameEl.textContent = user.full_name;
            }
        })
        .catch(() => { window.location.href = '/login'; });

    // Fetch Stores for selector
    fetch('/api/stores')
        .then(res => res.json())
        .then(stores => {
            const select = document.getElementById('storeSelect');
            stores.forEach(store => {
                const opt = document.createElement('option');
                opt.value = store.id;
                opt.textContent = store.name;
                select.appendChild(opt);
            });
        });

    // Main data loading function
    const loadDashboardData = (storeId = null) => {
        const url = storeId ? `/api/dashboard?store_id=${storeId}` : '/api/dashboard';
        
        fetch(url)
            .then(res => res.json())
            .then(data => {
                // KPIs
                document.getElementById('kpiRevenue').textContent = `₹${data.total_revenue.toLocaleString('en-IN')}`;
                document.getElementById('kpiUnits').textContent = data.units_sold.toLocaleString('en-IN');
                document.getElementById('kpiStockouts').textContent = data.stockout_risks;
                document.getElementById('kpiOverstocks').textContent = data.overstock_count;

                // Alerts
                const alertsList = document.getElementById('alertsList');
                alertsList.innerHTML = '';
                if(data.priority_alerts.length === 0) {
                    alertsList.innerHTML = '<div class="loading">No alerts at this time.</div>';
                } else {
                    data.priority_alerts.forEach(alert => {
                        let icon = '⚠️';
                        if(alert.type === 'Overstock') icon = '📦';
                        if(alert.type === 'Sales Spike') icon = '📈';
                        if(alert.type === 'Sales Drop') icon = '📉';
                        if(alert.type === 'Critical Stockout') icon = '🚨';

                        const div = document.createElement('div');
                        div.className = `alert-item alert-${alert.severity}`;
                        div.innerHTML = `
                            <div class="alert-header">
                                <span class="alert-type">${icon} ${alert.type}</span>
                                <span class="badge badge-${alert.severity.toLowerCase()}">${alert.severity}</span>
                            </div>
                            <div class="alert-product">${alert.product_name} <span style="font-size:0.8rem;font-weight:normal;color:var(--text-muted)">(${alert.store_name})</span></div>
                            <div class="alert-details">
                                ${alert.days_remaining !== undefined ? 
                                    `<span><strong>Stock:</strong> ${alert.current_stock}</span>
                                     <span><strong>Avg Sales:</strong> ${alert.avg_daily_sales}/day</span>
                                     <span><strong>Remaining:</strong> ${alert.days_remaining} days</span>` : 
                                    `<span>${alert.details}</span>`
                                }
                            </div>
                            <div class="alert-action">
                                ${getRecommendation(alert)}
                            </div>
                        `;
                        alertsList.appendChild(div);
                    });
                }

                // Top Products
                const topProductsList = document.getElementById('topProductsList');
                topProductsList.innerHTML = '';
                data.top_products.forEach(p => {
                    topProductsList.innerHTML += `
                        <div class="top-product-item">
                            <div>
                                <strong>${p.product_name}</strong>
                                <div style="font-size:0.8rem;color:var(--text-muted)">${p.store_name}</div>
                            </div>
                            <div>
                                <strong>${p.total_30d_sales}</strong> units
                            </div>
                        </div>
                    `;
                });

                // Chart (Health Breakdown)
                const total = data.total_products || 1;
                const riskPct = (data.stockout_risks / total) * 100;
                const overPct = (data.overstock_count / total) * 100;
                const healthyPct = 100 - riskPct - overPct;

                document.getElementById('barCritical').style.height = `${riskPct}%`;
                document.getElementById('barHealthy').style.height = `${healthyPct}%`;
                document.getElementById('barOverstock').style.height = `${overPct}%`;
            });
            
        loadInventoryTable(storeId);
        loadSalesTrend(storeId);
        loadSmartReorderAndRisk(storeId);
    };

    const getRecommendation = (alert) => {
        if(alert.type === 'Critical Stockout') return '<strong>Action:</strong> Reorder immediately.';
        if(alert.type === 'Stockout Risk') return '<strong>Action:</strong> Prepare to reorder.';
        if(alert.type === 'Overstock') return '<strong>Action:</strong> Consider promotion or transfer.';
        if(alert.type === 'Sales Spike') return '<strong>Action:</strong> Investigate demand increase.';
        if(alert.type === 'Sales Drop') return '<strong>Action:</strong> Review inventory & trends.';
        return '';
    };

    const loadInventoryTable = (storeId = null) => {
        const url = storeId ? `/api/inventory?store_id=${storeId}` : '/api/inventory';
        fetch(url)
            .then(res => res.json())
            .then(data => {
                const tbody = document.getElementById('inventoryTableBody');
                tbody.innerHTML = '';
                
                // Sort by days remaining ascending
                data.sort((a,b) => a.days_remaining - b.days_remaining);
                
                data.forEach(item => {
                    let statusHtml = '<span class="badge badge-healthy">Healthy</span>';
                    if(item.days_remaining <= 1) statusHtml = '<span class="badge badge-critical">Critical</span>';
                    else if(item.days_remaining <= 3) statusHtml = '<span class="badge badge-warning">Low Stock</span>';
                    else if(item.days_remaining > 60) statusHtml = '<span class="badge badge-info">Overstock</span>';

                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${item.product_name}</td>
                        <td>${item.store_name}</td>
                        <td>${item.current_stock}</td>
                        <td>${item.avg_daily_sales}</td>
                        <td>${item.days_remaining === 999 ? '999+' : item.days_remaining}</td>
                        <td>${statusHtml}</td>
                    `;
                    tbody.appendChild(tr);
                });
            });
    };

    // ============== SALES TREND ==============
    const loadSalesTrend = (storeId = null) => {
        const url = storeId ? `/api/sales/trend?store_id=${storeId}` : '/api/sales/trend';
        const chartEl = document.getElementById('salesTrendChart');
        const summaryEl = document.getElementById('salesTrendSummary');
        const xAxisEl = document.getElementById('salesTrendXAxis');

        fetch(url)
            .then(r => r.json())
            .then(data => {
                const trend = data.trend || [];
                if (trend.length === 0) {
                    chartEl.innerHTML = '<div class="loading">No sales data available for this period.</div>';
                    summaryEl.textContent = '';
                    return;
                }

                // Summary text
                const pct = data.pct_change;
                const direction = pct > 0 ? '▲' : pct < 0 ? '▼' : '→';
                const color = pct > 0 ? 'var(--success)' : pct < 0 ? 'var(--critical)' : 'var(--text-muted)';
                summaryEl.innerHTML = `Sales <strong style="color:${color}">${direction} ${Math.abs(pct)}%</strong> compared to the previous period (₹${data.current_period_revenue.toLocaleString('en-IN')} this period vs ₹${data.prev_period_revenue.toLocaleString('en-IN')} last period).`;

                // Determine 30-days-ago for coloring
                const thirtyDaysAgo = new Date();
                thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

                // Chart bars
                const maxRev = Math.max(...trend.map(d => d.revenue), 1);
                chartEl.innerHTML = '';
                trend.forEach(d => {
                    const barDate = new Date(d.date);
                    const isPrev = barDate < thirtyDaysAgo;
                    const heightPct = Math.max((d.revenue / maxRev) * 100, 2);
                    const bar = document.createElement('div');
                    bar.className = `trend-bar${isPrev ? ' prev-period' : ''}`;
                    bar.style.height = `${heightPct}%`;
                    bar.title = `${d.date}\n₹${d.revenue.toLocaleString('en-IN')} | ${d.units} units`;
                    chartEl.appendChild(bar);
                });

                // X-axis labels (first and last dates)
                if (trend.length > 0) {
                    xAxisEl.innerHTML = `<span>${trend[0].date}</span><span>← Prev 30d | Current 30d →</span><span>${trend[trend.length - 1].date}</span>`;
                }
            })
            .catch(() => {
                chartEl.innerHTML = '<div class="loading">Failed to load trend data.</div>';
            });
    };

    // ============== SMART REORDER & RISK SCORE ==============
    const loadSmartReorderAndRisk = (storeId = null) => {
        const url = storeId ? `/api/inventory?store_id=${storeId}` : '/api/inventory';
        const reorderEl = document.getElementById('smartReorderList');
        const riskEl = document.getElementById('inventoryRiskList');

        fetch(url)
            .then(r => r.json())
            .then(metrics => {
                // Smart Reorder – only show CRITICAL/HIGH/MEDIUM priority
                const reorderItems = metrics
                    .filter(m => m.reorder_priority !== 'LOW' || m.recommended_reorder > 0)
                    .sort((a, b) => {
                        const order = {CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3};
                        return (order[a.reorder_priority] || 3) - (order[b.reorder_priority] || 3);
                    });

                if (reorderItems.length === 0) {
                    reorderEl.innerHTML = '<div class="loading">All products are well stocked. No reorder needed.</div>';
                } else {
                    reorderEl.innerHTML = reorderItems.map(m => {
                        const noSalesData = m.avg_daily_sales === 0;
                        return `<div class="reorder-card">
                            <div class="reorder-card-info">
                                <div class="reorder-card-name">${m.product_name} <span style="font-size:0.78rem;color:var(--text-muted)">@ ${m.store_name}</span></div>
                                <div class="reorder-card-meta">
                                    Stock: <strong>${m.current_stock}</strong> &nbsp;|
                                    Avg Sales: <strong>${noSalesData ? 'N/A' : m.avg_daily_sales + '/day'}</strong> &nbsp;|
                                    Days Left: <strong>${noSalesData ? 'Insufficient data' : (m.days_remaining === 999 ? '999+' : m.days_remaining)}</strong>
                                </div>
                            </div>
                            <div class="reorder-card-action">
                                <div class="reorder-qty">${m.recommended_reorder}</div>
                                <div class="reorder-qty-label">units to reorder</div>
                                <div class="priority-badge priority-${m.reorder_priority}">${m.reorder_priority}</div>
                            </div>
                        </div>`;
                    }).join('');
                }

                // Inventory Risk Score
                const sortedByRisk = [...metrics].sort((a, b) => b.risk_score - a.risk_score);
                riskEl.innerHTML = sortedByRisk.map(m => {
                    const catColor = {
                        Critical: 'var(--critical)',
                        High: 'var(--warning)',
                        Medium: 'var(--info)',
                        Low: 'var(--success)'
                    }[m.risk_category] || 'var(--text-muted)';

                    const blocks = Math.round(m.risk_score / 10);
                    const filled = '█'.repeat(blocks);
                    const empty = '░'.repeat(10 - blocks);

                    return `<div class="risk-row">
                        <div class="risk-row-header">
                            <span><strong>${m.product_name}</strong> <span style="font-size:0.75rem;color:var(--text-muted)">@ ${m.store_name}</span></span>
                            <span>
                                <span style="font-family:monospace;letter-spacing:1px;color:${catColor}">${filled}${empty}</span>
                                <span class="risk-category-label" style="color:${catColor}">${m.risk_score}/100 ${m.risk_category.toUpperCase()}</span>
                            </span>
                        </div>
                        <div class="risk-bar-track">
                            <div class="risk-bar-fill risk-${m.risk_category}" style="width:${m.risk_score}%"></div>
                        </div>
                    </div>`;
                }).join('');
            })
            .catch(() => {
                reorderEl.innerHTML = '<div class="loading">Failed to load data.</div>';
                riskEl.innerHTML = '<div class="loading">Failed to load data.</div>';
            });
    };

    // Initial Load
    loadDashboardData();

    // Store change event
    document.getElementById('storeSelect').addEventListener('change', (e) => {
        const val = e.target.value;
        loadDashboardData(val ? parseInt(val) : null);
    });

    // Chat Logic
    const chatInput = document.getElementById('chatInput');
    const chatSendBtn = document.getElementById('chatSendBtn');
    const chatHistory = document.getElementById('chatHistory');

    const appendMessage = (type, htmlContent) => {
        const div = document.createElement('div');
        div.className = `chat-message ${type}`;
        div.innerHTML = htmlContent;
        chatHistory.appendChild(div);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    };

    const sendMessage = (text) => {
        if(!text.trim()) return;
        
        appendMessage('user', text);
        chatInput.value = '';
        chatInput.disabled = true;
        chatSendBtn.disabled = true;
        
        const storeId = document.getElementById('storeSelect').value;
        const payload = {
            message: text,
            store_id: storeId ? parseInt(storeId) : null
        };

        const loadingId = 'loading-' + Date.now();
        appendMessage('ai', `<div id="${loadingId}" class="loading">Analyzing local data...</div>`);

        fetch('/api/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        })
        .then(res => res.json())
        .then(data => {
            document.getElementById(loadingId).remove();
            
            let html = `<div class="ai-answer">${data.answer}</div>`;
            
            if(data.evidence && data.evidence.length > 0) {
                html += `<div class="ai-evidence"><strong>Evidence:</strong><ul>`;
                data.evidence.forEach(ev => {
                    const productStr = ev.product ? `[${ev.product}] ` : '';
                    html += `<li>${productStr}${ev.metric}: ${ev.value} <small>(${ev.source})</small></li>`;
                });
                html += `</ul></div>`;
            }

            if(data.recommendations && data.recommendations.length > 0) {
                data.recommendations.forEach(rec => {
                    html += `
                        <div class="ai-recommendation">
                            <div class="ai-rec-action">Action: ${rec}</div>
                        </div>
                    `;
                });
            }

            if(data.data_limitations && data.data_limitations.length > 0) {
                html += `<div class="ai-limitations"><strong>Limitations:</strong> ${data.data_limitations.join(', ')}</div>`;
            }

            appendMessage('ai', html);
        })
        .catch(err => {
            document.getElementById(loadingId).remove();
            appendMessage('ai', `<div class="ai-limitations">Error connecting to copilot. Please check backend logs.</div>`);
        })
        .finally(() => {
            chatInput.disabled = false;
            chatSendBtn.disabled = false;
            chatInput.focus();
        });
    };

    chatSendBtn.addEventListener('click', () => sendMessage(chatInput.value));
    chatInput.addEventListener('keypress', (e) => {
        if(e.key === 'Enter') sendMessage(chatInput.value);
    });

    // Suggested Questions
    document.querySelectorAll('.suggested-q').forEach(btn => {
        btn.addEventListener('click', (e) => {
            sendMessage(e.target.textContent);
        });
    });

    // ==================== SCENARIO NAVIGATION ====================
    const mainContent = document.querySelector('.main-content');
    const scenarioPanel = document.getElementById('scenarioPanel');
    const scenarioPanelInner = document.getElementById('scenarioPanelInner');
    const backBtn = document.getElementById('backToDashboardBtn');

    const SCENARIO_QUESTIONS = {
        'wireless-mouse':    'Which products need immediate reorder?',
        'premium-detergent': 'Which products are overstocked?',
        'chocolate-box':     'Did any product have a sales spike?',
        'coffee-pack':       'Show me products with declining sales.',
    };

    const showScenario = (scenarioId) => {
        // Highlight active button
        document.querySelectorAll('.scenario-btn').forEach(b => b.classList.remove('active'));
        const activeBtn = document.querySelector(`[data-scenario="${scenarioId}"]`);
        if (activeBtn) activeBtn.classList.add('active');

        // Show back button
        backBtn.style.display = 'block';

        // Swap panels
        mainContent.style.display = 'none';
        scenarioPanel.style.display = 'block';
        scenarioPanelInner.innerHTML = '<div class="loading">Loading scenario data...</div>';

        fetch(`/api/scenarios/${scenarioId}`)
            .then(r => r.json())
            .then(data => {
                if (data.error) {
                    scenarioPanelInner.innerHTML = `<div class="loading">${data.error}</div>`;
                    return;
                }
                renderScenario(data);
            })
            .catch(err => {
                scenarioPanelInner.innerHTML = '<div class="loading">Failed to load scenario data.</div>';
            });
    };

    const goBackToDashboard = () => {
        mainContent.style.display = 'flex';
        scenarioPanel.style.display = 'none';
        backBtn.style.display = 'none';
        document.querySelectorAll('.scenario-btn').forEach(b => b.classList.remove('active'));
    };

    const renderScenario = (data) => {
        const rec = data.recommendation || {};
        const summary = data.summary || {};
        const severity = rec.severity || 'INFO';

        // Determine type label
        const typeLabels = {
            stockout: '🚨 Critical Stockout Scenario',
            overstock: '📦 Overstock Scenario',
            spike: '📈 Sales Spike Scenario',
            drop: '📉 Sales Drop Scenario',
        };
        const typeLabel = typeLabels[data.scenario_type] || 'Scenario';

        let html = `
            <div class="scenario-header">
                <div>
                    <h2>${data.product_name}</h2>
                    <div style="color:var(--text-muted);font-size:0.9rem;margin-top:4px">${typeLabel} &mdash; ${data.category} &mdash; Supplier: ${data.supplier}</div>
                </div>
                <span class="scenario-severity severity-${severity}">${severity}</span>
            </div>

            <div class="scenario-summary-grid">
                <div class="scenario-stat-card">
                    <div class="label">Total Stock (all stores)</div>
                    <div class="value">${summary.total_stock} units</div>
                </div>
                <div class="scenario-stat-card">
                    <div class="label">Avg Daily Sales (30d)</div>
                    <div class="value">${summary.avg_daily_sales}/day</div>
                </div>
                <div class="scenario-stat-card">
                    <div class="label">Prev Period Avg</div>
                    <div class="value">${summary.prev_avg_daily}/day</div>
                </div>
                <div class="scenario-stat-card">
                    <div class="label">Days Remaining</div>
                    <div class="value" style="color:${summary.days_remaining <= 3 ? 'var(--critical)' : summary.days_remaining > 60 ? 'var(--info)' : 'var(--success)'}">${summary.days_remaining === 999 ? '999+' : summary.days_remaining} days</div>
                </div>
                <div class="scenario-stat-card">
                    <div class="label">30-Day Units Sold</div>
                    <div class="value">${summary.total_30d_sales}</div>
                </div>
                <div class="scenario-stat-card">
                    <div class="label">Price</div>
                    <div class="value">₹${data.price}</div>
                </div>
            </div>
        `;

        // Recommendation card
        if (rec.action) {
            html += `
                <div class="scenario-rec-card">
                    <h3>Recommendation</h3>
                    <div class="scenario-rec-action">${rec.action}</div>
                    <div class="scenario-rec-reason">${rec.reason}</div>
                    <div class="scenario-evidence-list">
                        ${(rec.evidence || []).map(e =>
                            `<div class="scenario-evidence-chip"><span class="chip-label">${e.fact}:</span><span class="chip-value">${e.value}</span></div>`
                        ).join('')}
                    </div>
                </div>
            `;
        }

        // Store breakdown table
        if (data.store_breakdown && data.store_breakdown.length > 0) {
            html += `
                <div class="scenario-rec-card">
                    <h3>Store Breakdown</h3>
                    <table class="scenario-store-table">
                        <thead>
                            <tr>
                                <th>Store</th>
                                <th>Stock</th>
                                <th>Avg Sales/day</th>
                                <th>Prev Avg/day</th>
                                <th>Days Left</th>
                                <th>Change</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.store_breakdown.map(s => {
                                let changeBadge = '';
                                if (s.change_pct !== null) {
                                    const color = s.change_pct > 0 ? 'var(--success)' : 'var(--critical)';
                                    changeBadge = `<span style="color:${color}">${s.change_pct > 0 ? '+' : ''}${s.change_pct}%</span>`;
                                } else {
                                    changeBadge = '<span style="color:var(--text-muted)">N/A</span>';
                                }
                                let daysColor = s.days_remaining <= 3 ? 'var(--critical)' : s.days_remaining > 60 ? 'var(--info)' : 'var(--text-main)';
                                return `<tr>
                                    <td>${s.store_name}</td>
                                    <td>${s.current_stock}</td>
                                    <td>${s.avg_daily_sales}</td>
                                    <td>${s.prev_avg_daily}</td>
                                    <td style="color:${daysColor}">${s.days_remaining === 999 ? '999+' : s.days_remaining}</td>
                                    <td>${changeBadge}</td>
                                </tr>`;
                            }).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        }

        scenarioPanelInner.innerHTML = html;
    };

    // Bind scenario buttons
    document.querySelectorAll('.scenario-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            showScenario(btn.dataset.scenario);
        });
    });

    // Back button
    backBtn.addEventListener('click', goBackToDashboard);

    // ==================== DATA ENTRY MODAL ====================
    const modal = document.getElementById('dataEntryModal');
    const openModalBtn = document.getElementById('openAddDataModalBtn');
    const closeModalBtn = document.getElementById('closeAddDataModalBtn');
    const modalMessage = document.getElementById('modal-message');

    // Populate dropdowns
    const populateDropdowns = async () => {
        try {
            const [storesRes, productsRes] = await Promise.all([
                fetch('/api/stores'),
                fetch('/api/products/list')
            ]);
            const stores = await storesRes.json();
            const products = await productsRes.json();

            const storeOptions = stores.map(s => `<option value="${s.id}">${s.name}</option>`).join('');
            const productOptions = products.map(p => `<option value="${p.id}">${p.name}</option>`).join('');

            document.getElementById('prod-store').innerHTML = storeOptions;
            document.getElementById('sale-store').innerHTML = storeOptions;
            document.getElementById('inv-store').innerHTML = storeOptions;

            document.getElementById('sale-product').innerHTML = productOptions;
            document.getElementById('inv-product').innerHTML = productOptions;
        } catch (err) {
            console.error('Error loading dropdowns', err);
        }
    };

    openModalBtn.addEventListener('click', () => {
        modal.style.display = 'flex';
        modalMessage.className = 'modal-message';
        modalMessage.textContent = '';
        populateDropdowns();
    });

    closeModalBtn.addEventListener('click', () => {
        modal.style.display = 'none';
    });

    // Close if clicked outside
    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });

    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
            
            btn.classList.add('active');
            document.getElementById(btn.dataset.target).style.display = 'block';
            modalMessage.textContent = '';
        });
    });

    // Form handlers
    const handleFormSubmit = async (e, endpoint, getPayload) => {
        e.preventDefault();
        modalMessage.className = 'modal-message loading';
        modalMessage.textContent = 'Saving...';
        
        try {
            const payload = getPayload();
            const res = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            
            if (res.ok) {
                modalMessage.className = 'modal-message success';
                modalMessage.textContent = data.message || 'Saved successfully!';
                e.target.reset(); // Reset form
                // Reload dashboard
                loadDashboardData(document.getElementById('storeSelect').value || null);
                // Wait a bit, then close modal
                setTimeout(() => {
                    modal.style.display = 'none';
                }, 1500);
            } else {
                modalMessage.className = 'modal-message error';
                modalMessage.textContent = data.detail || 'Error saving data.';
            }
        } catch (err) {
            modalMessage.className = 'modal-message error';
            modalMessage.textContent = 'Network error.';
        }
    };

    document.getElementById('form-product').addEventListener('submit', (e) => {
        handleFormSubmit(e, '/api/products', () => ({
            name: document.getElementById('prod-name').value,
            category: document.getElementById('prod-cat').value,
            store_id: parseInt(document.getElementById('prod-store').value),
            price: parseFloat(document.getElementById('prod-price').value),
            current_stock: parseInt(document.getElementById('prod-stock').value),
            reorder_level: parseInt(document.getElementById('prod-reorder').value)
        }));
    });

    document.getElementById('form-sale').addEventListener('submit', (e) => {
        handleFormSubmit(e, '/api/sales', () => ({
            product_id: parseInt(document.getElementById('sale-product').value),
            store_id: parseInt(document.getElementById('sale-store').value),
            date: document.getElementById('sale-date').value,
            units_sold: parseInt(document.getElementById('sale-qty').value),
            revenue: parseFloat(document.getElementById('sale-revenue').value)
        }));
    });

    document.getElementById('form-inventory').addEventListener('submit', (e) => {
        handleFormSubmit(e, '/api/inventory', () => ({
            product_id: parseInt(document.getElementById('inv-product').value),
            store_id: parseInt(document.getElementById('inv-store').value),
            quantity: parseInt(document.getElementById('inv-stock').value),
            reorder_level: parseInt(document.getElementById('inv-reorder').value)
        }));
    });

});
