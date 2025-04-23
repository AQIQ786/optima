frappe.ui.form.on('External Database Viewer', {
    refresh: function (frm) {
        frm.add_custom_button(__('Fetch Databases'), function () {
            frappe.call({
                method: "optima.optima.doctype.external_database_viewer.external_database_viewer.fetch_databases",
                args: {
                    server: frm.doc.server_ip_address,
                    port: frm.doc.port,
                    username: frm.doc.username,
                    password: frm.doc.password
                },
                callback: function (response) {
                    console.log("Databases response:", response);

                    if (response.message && !response.message.error) {
                        let databases = response.message;
                        let db_html = `
                            <div id="databases-container" style="display: flex; flex-wrap: wrap; gap: 20px; opacity: 0; animation: fadeIn 1s forwards;">
                        `;

                        const colors = ['#f8d210', '#ff6f61', '#6a0572', '#16a596', '#2d6a4f', '#ef476f', '#073b4c', '#118ab2'];
                        databases.forEach((db, index) => {
                            const color = colors[index % colors.length];
                            db_html += `
                                <div class="db-card" style="background-color: ${color}; color: #fff; padding: 20px; border-radius: 15px;  text-align: center; cursor: pointer; transition: transform 0.3s, box-shadow 0.3s;"
                                    onmouseover="this.style.transform='scale(1.05)'; this.style.boxShadow='0 8px 15px rgba(0, 0, 0, 0.3)';"
                                    onmouseout="this.style.transform='scale(1)'; this.style.boxShadow='0 4px 8px rgba(0, 0, 0, 0.15)';"
                                    onclick="showTables('${db.name.replace(/'/g, "\\'")}')">
                                    <div style="font-size: 1.2em; font-weight: bold;">${db.name}</div>
                                </div>
                            `;
                        });
                        db_html += `</div>`;
                        frm.fields_dict['databases'].html(db_html);

                        setTimeout(() => {
                            document.getElementById('databases-container').style.opacity = 1;
                        }, 100);
                    } else {
                        frappe.msgprint("Error fetching databases: " + response.message.error);
                    }
                }
            });
        });
    }
});

// Function to display tables for the selected database
window.showTables = function(database) {
    frappe.call({
        method: "optima.optima.doctype.external_database_viewer.external_database_viewer.fetch_tables",
        args: {
            server: cur_frm.doc.server_ip_address,
            port: cur_frm.doc.port,
            username: cur_frm.doc.username,
            password: cur_frm.doc.password,
            database: database
        },
        callback: function(response) {
            if (response.message && !response.message.error) {
                let tables = response.message;
                let table_html = `
                    <div style="padding: 20px; animation: slideInUp 0.5s;">
                        <h3 style="color: #333; text-align: center; margin-bottom: 20px;">Tables in <span style="color: #007bff;">${database}</span></h3>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px;">
                `;

                const tableColors = ['#00afb9', '#ef476f', '#ffd166', '#06d6a0', '#118ab2', '#073b4c'];
                tables.forEach((table, index) => {
                    const color = tableColors[index % tableColors.length];
                    table_html += `
                        <div class="table-card" style="background-color: ${color}; padding: 10px; border-radius: 10px; color: #fff; text-align: center; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1); cursor: pointer;"
                            onclick="showColumns('${database}', '${table.table_name}')">
                            ${table.table_name}
                        </div>
                    `;
                });
                table_html += `</div></div>`;

                cur_frm.fields_dict['tables_container'].html(table_html);
            } else {
                frappe.msgprint("Error fetching tables: " + response.message.error);
            }
        }
    });
};

// Function to display columns of a selected table
window.showColumns = function(database, table) {
    frappe.call({
        method: "optima.optima.doctype.external_database_viewer.external_database_viewer.fetch_columns",
        args: {
            server: cur_frm.doc.server_ip_address,
            port: cur_frm.doc.port,
            username: cur_frm.doc.username,
            password: cur_frm.doc.password,
            database: database,
            table: table
        },
        callback: function(response) {
            if (response.message && !response.message.error) {
                let columns = response.message;
                let column_html = `
                    <div style="padding: 20px; background-color: #fff;">
                        <h3 style="color: #333; text-align: center; margin-bottom: 20px;">Columns in <span style="color: #007bff;">${table}</span> Table</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr style="background-color: #007bff; color: #fff;">
                                <th style="padding: 10px; border: 1px solid #ddd;">Column Name</th>
                                <th style="padding: 10px; border: 1px solid #ddd;">Data Type</th>
                            </tr>
                `;

                columns.forEach(col => {
                    column_html += `
                        <tr style="text-align: center;">
                            <td style="padding: 10px; border: 1px solid #ddd;">${col.column_name}</td>
                            <td style="padding: 10px; border: 1px solid #ddd;">${col.data_type}</td>
                        </tr>
                    `;
                });
                column_html += `</table></div>`;

                // Add a button to show the latest 5 items and download Excel
                column_html += `
                    <div style="text-align: center; margin-top: 20px;">
                        <button class="btn btn-primary" onclick="showLatestItems('${database}', '${table}')">Show Latest Items</button>
                        <button class="btn btn-success" onclick="downloadExcel('${table}')">Download Excel</button>
                    </div>
                `;

                // Display the columns in a modal
                frappe.msgprint({
                    title: `Columns in ${table}`,
                    indicator: 'green',
                    message: column_html,
                    primary_action: {
                        label: 'Close',
                        action() {
                            frappe.hide_msgprint();
                        }
                    }
                });
            } else {
                frappe.msgprint("Error fetching columns: " + response.message.error);
            }
        }
    });
};

// Function to fetch and display the latest 5 items from the table
window.showLatestItems = function(database, table) {
    frappe.call({
        method: "optima.optima.doctype.external_database_viewer.external_database_viewer.fetch_latest_items",
        args: {
            server: cur_frm.doc.server_ip_address,
            port: cur_frm.doc.port,
            username: cur_frm.doc.username,
            password: cur_frm.doc.password,
            database: database,
            table: table
        },
        callback: function(response) {
            if (response.message && !response.message.error) {
                let data = response.message;
                let items_html = `
                    <div style="padding: 20px; background-color: #fff;">
                        <h3 style="color: #333; text-align: center; margin-bottom: 20px;">Latest 5 Items in <span style="color: #007bff;">${table}</span></h3>
                        <table id="latest-items-table" style="width: 100%; border-collapse: collapse; border: 1px solid #ddd;">
                            <tr style="background-color: #f8f9fa; color: #333;">
                `;

                // Add column headers
                data.columns.forEach(column => {
                    items_html += `<th style="padding: 10px; border: 1px solid #ddd;">${column}</th>`;
                });

                items_html += `</tr>`;

                // Add rows for the latest items
                data.items.forEach(item => {
                    items_html += `<tr style="text-align: center;">`;
                    item.forEach(value => {
                        items_html += `<td style="padding: 10px; border: 1px solid #ddd;">${value}</td>`;
                    });
                    items_html += `</tr>`;
                });

                items_html += `</table></div>`;

                // Add buttons for actions
                items_html += `
                    <div style="text-align: center; margin-top: 20px;">
                        <button class="btn btn-success" onclick="downloadExcel('${table}')">Download Excel</button>
                    </div>
                `;

                // Display the items in a modal
                frappe.msgprint({
                    title: `Latest 5 Items in ${table}`,
                    indicator: 'blue',
                    message: items_html,
                    primary_action: {
                        label: 'Close',
                        action() {
                            frappe.hide_msgprint();
                        }
                    }
                });
            } else {
                frappe.msgprint("Error fetching items: " + response.message.error);
            }
        }
    });
};

// Function to download the displayed data as an Excel file
window.downloadExcel = function(table) {
    let tableElement = document.getElementById('latest-items-table');
    if (!tableElement) {
        frappe.msgprint("No data available to download.");
        return;
    }

    // Convert table to CSV format
    let csvContent = Array.from(tableElement.rows)
        .map(row => Array.from(row.cells)
            .map(cell => `"${cell.textContent.trim()}"`)
            .join(",")
        )
        .join("\n");

    // Create a downloadable file
    let blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    let link = document.createElement("a");
    let url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", `${table}_data.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
};
