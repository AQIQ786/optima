// Copyright (c) 2024, Ronoh and contributors
// For license information, please see license.txt

frappe.ui.form.on("Optima Settings", {
	refresh(frm) {
		frm.add_custom_button(__('Test Connection'), function() {
			frappe.call({
				method: 'test_connection',
				doc: frm.doc,
				callback: function(r) {
					if (r.message.success) {
						frappe.msgprint({
							title: __('Success'),
							indicator: 'green',
							message: r.message.message
						});
					} else {
						frappe.msgprint({
							title: __('Failed'),
							indicator: 'red',
							message: r.message.message
						});
					}
				}
			});
		});

		let $dashboard = frm.dashboard.add_section(`
			<div class="dashboard-section">
				<div class="section-head">Database Information</div>
				<div class="databases-section">
					<p class="text-muted">Click "Show Databases" to view available databases</p>
				</div>
			</div>
		`);

		frm.add_custom_button(__('Show Databases'), function() {
			frappe.call({
				method: 'get_databases',
				doc: frm.doc,
				callback: function(r) {
					if (r.message && r.message.success) {
						let databases = r.message.databases;
						let html = '<div class="database-list">';
						databases.forEach(db => {
							html += `
								<div class="database-item" data-database="${db}">
									<div class="database-header">
										<span class="collapse-indicator">▶</span>
										<span class="database-name">${db}</span>
										<button class="btn btn-xs btn-default show-tables" 
											data-database="${db}">Show Tables</button>
									</div>
									<div class="database-content" style="display: none;"></div>
								</div>`;
						});
						html += '</div>';
						
						$dashboard.find('.databases-section').html(html);

						$dashboard.find('.database-header').on('click', function(e) {
							if (!$(e.target).hasClass('btn')) {
								let $item = $(this).closest('.database-item');
								let $content = $item.find('.database-content');
								let $indicator = $(this).find('.collapse-indicator');
								
								$content.slideToggle(200);
								$indicator.text($content.is(':visible') ? '▼' : '▶');
							}
						});

						$dashboard.find('.show-tables').on('click', function(e) {
							e.stopPropagation();
							let $btn = $(this);
							let database = $btn.data('database');
							let $content = $btn.closest('.database-item').find('.database-content');
							let $indicator = $btn.closest('.database-header').find('.collapse-indicator');
							
							frm.call('get_tables', { database: database })
								.then(r => {
									if (r.message && r.message.success) {
										let tables = r.message.tables;
										let tableHtml = '<div class="table-list">';
										tables.forEach(table => {
											tableHtml += `
												<div class="table-item">
													<div class="table-header">
														<span class="collapse-indicator">▶</span>
														<span class="table-name">${table}</span>
														<button class="btn btn-xs btn-default show-fields"
															data-table="${table}">Show Fields</button>
													</div>
													<div class="table-fields" style="display: none;"></div>
												</div>`;
										});
										tableHtml += '</div>';
										
										$content.html(tableHtml);
										$content.show();
										$indicator.text('▼');

										$content.find('.table-header').on('click', function(e) {
											if (!$(e.target).hasClass('btn')) {
												let $fields = $(this).siblings('.table-fields');
												let $indicator = $(this).find('.collapse-indicator');
												
												$fields.slideToggle(200);
												$indicator.text($fields.is(':visible') ? '▼' : '▶');
											}
										});

										$content.find('.show-fields').on('click', function(e) {
											e.stopPropagation();
											let $btn = $(this);
											let table = $btn.data('table');
											let $fields = $btn.closest('.table-item').find('.table-fields');
											let $indicator = $btn.closest('.table-header').find('.collapse-indicator');

											frm.call('get_table_fields', {
												database: database,
												table: table
											}).then(r => {
												if (r.message && r.message.success) {
													let fields = r.message.fields;
													let fieldsHtml = '<div class="fields-list">';
													fields.forEach(field => {
														fieldsHtml += `
															<div class="field-item">
																<span class="field-name">${field.name}</span>
																<span class="field-type">${field.type}</span>
																${field.is_nullable ? '<span class="field-nullable">Nullable</span>' : ''}
																${field.is_primary_key ? '<span class="field-pk">PK</span>' : ''}
															</div>`;
													});
													fieldsHtml += '</div>';
													
													$fields.html(fieldsHtml);
													$fields.show();
													$indicator.text('▼');
												}
											});
										});
									}
								});
						});
					}
				}
			});
		});

		// frm.add_custom_button(__('Show Orders'), function() {
		// 	frappe.call({
		// 		method: 'get_orders',
		// 		doc: frm.doc,
		// 		callback: function(r) {
		// 			if (r.message && r.message.success) {
		// 				console.log(r.message.orders)
						
		// 			}
		// 		}
		// 	});
		// });

		frm.add_custom_button(__('Dump Database Schema'), function() {
			let d = new frappe.ui.Dialog({
				title: 'Select Database to Dump',
				fields: [
					{
						label: 'Database',
						fieldname: 'database',
						fieldtype: 'Select',
						options: [],
						reqd: 1
					}
				],
				primary_action_label: 'Dump Schema',
				primary_action(values) {
					frappe.call({
						method: 'dump_database_schema',
						doc: frm.doc,
						args: {
							database: values.database
						},
						freeze: true,
						freeze_message: __('Generating database schema...'),
						callback: function(r) {
							if (r.message && r.message.success) {
								// Download the generated file
								window.open(r.message.file_url);
								frappe.msgprint({
									title: __('Success'),
									indicator: 'green',
									message: __('Database schema has been generated successfully.')
								});
							} else {
								frappe.msgprint({
									title: __('Failed'),
									indicator: 'red',
									message: r.message.message || __('Failed to generate database schema.')
								});
							}
							d.hide();
						}
					});
				}
			});

			// Fetch databases to populate the select field
			frappe.call({
				method: 'get_databases',
				doc: frm.doc,
				callback: function(r) {
					if (r.message && r.message.success) {
						d.set_df_property('database', 'options', r.message.databases);
					}
				}
			});

			d.show();
		}).addClass('btn-primary');

		// Add Insert Test Order button
		// frm.add_custom_button(__('Insert Test Order'), function() {
		// 	frappe.confirm(
		// 		'This will insert a test order into the Optima database. Continue?',
		// 		function() {
		// 			frappe.call({
		// 				method: 'insert_test_order',
		// 				doc: frm.doc,
		// 				freeze: true,
		// 				freeze_message: __('Creating test order...'),
		// 				callback: function(r) {
		// 					if (r.message && r.message.success) {
		// 						frappe.msgprint({
		// 							title: __('Success'),
		// 							indicator: 'green',
		// 							message: r.message.message
		// 						});
		// 					} else {
		// 						frappe.msgprint({
		// 							title: __('Failed'),
		// 							indicator: 'red',
		// 							message: r.message.message
		// 						});
		// 					}
		// 				}
		// 			});
		// 		}
		// 	);
		// });

		if (!document.getElementById('optima-settings-style')) {
			const style = document.createElement('style');
			style.id = 'optima-settings-style';
			style.textContent = `
				.database-list {
					margin-top: 10px;
				}
				.database-item {
					border: 1px solid #d1d8dd;
					margin-bottom: 8px;
					border-radius: 4px;
					background: #f8f9fa;
				}
				.database-header, .table-header {
					padding: 8px;
					cursor: pointer;
					display: flex;
					align-items: center;
				}
				.database-header:hover, .table-header:hover {
					background: #eef0f2;
				}
				.collapse-indicator {
					margin-right: 8px;
					font-size: 10px;
					color: #6c757d;
				}
				.database-name {
					font-weight: bold;
					margin-right: 10px;
					color: #1a73e8;
					flex-grow: 1;
				}
				.table-list {
					padding: 8px 16px;
				}
				.table-item {
					border: 1px solid #e5e7eb;
					margin-bottom: 4px;
					border-radius: 4px;
				}
				.table-name {
					font-family: monospace;
					color: #555;
					flex-grow: 1;
				}
				.fields-list {
					padding: 8px 24px;
					background: #fff;
				}
				.field-item {
					padding: 4px 8px;
					display: flex;
					align-items: center;
					gap: 8px;
				}
				.field-item:hover {
					background: #f8f9fa;
				}
				.field-name {
					font-family: monospace;
					min-width: 150px;
				}
				.field-type {
					color: #6c757d;
					font-size: 0.9em;
				}
				.field-nullable, .field-pk {
					font-size: 0.8em;
					padding: 2px 4px;
					border-radius: 3px;
				}
				.field-nullable {
					background: #e9ecef;
					color: #495057;
				}
				.field-pk {
					background: #cff4fc;
					color: #055160;
				}
			`;
			document.head.appendChild(style);
		}
	}
});
