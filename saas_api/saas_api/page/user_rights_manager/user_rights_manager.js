frappe.pages['user-rights-manager'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'User Rights Manager',
		single_column: true
	});

    // Load users, roles, and existing rights
    frappe.call({
        method: 'saas_api.saas_api.page.user_rights_manager.user_rights_manager.load_data',
        callback: function(r) {
            const users = r.message.users;
            const roles = r.message.roles;
            const user_rights = r.message.user_rights;

            const userSelect = $('#user-select');
            const roleSelect = $('#role-select');
            const tableBody = $('#user-rights-table tbody');

            users.forEach(u => userSelect.append(`<option value="${u.name}">${u.full_name || u.name}</option>`));
            roles.forEach(r => roleSelect.append(`<option value="${r.name}">${r.name}</option>`));

            function refreshTable() {
                tableBody.empty();
                user_rights.forEach(ur => {
                    tableBody.append(`
                        <tr>
                            <td>${ur.user}</td>
                            <td>${ur.role}</td>
                            <td>
                                <button class="btn btn-sm btn-danger delete-user-right" data-name="${ur.name}">Delete</button>
                            </td>
                        </tr>
                    `);
                });
            }

            refreshTable();

            // Add / Update button
            $('#add-user-right').click(function() {
                const user = userSelect.val();
                const role = roleSelect.val();

                frappe.call({
                    method: 'frappe.client.insert',
                    args: {
                        doc: {
                            doctype: 'user rights',
                            user: user,
                            role: role
                        }
                    },
                    callback: function(res) {
                        if(res.message) {
                            user_rights.push(res.message);
                            refreshTable();
                            frappe.msgprint('User Right added / updated');
                        }
                    }
                });
            });

            // Delete button
            $(document).on('click', '.delete-user-right', function() {
                const name = $(this).data('name');
                frappe.call({
                    method: 'frappe.client.delete',
                    args: {
                        doctype: 'user rights',
                        name: name
                    },
                    callback: function() {
                        const index = user_rights.findIndex(u => u.name === name);
                        if(index > -1) user_rights.splice(index, 1);
                        refreshTable();
                        frappe.msgprint('User Right deleted');
                    }
                });
            });
        }
    });
        
}