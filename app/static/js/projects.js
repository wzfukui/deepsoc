// Projects page script with simple translation function
const translations = {
    create_from_template: '从模板创建',
    created_at_label: '创建时间:',
    invite_guest: '邀请访客',
    start_interview: '开始',
    edit: '编辑'
};

function t(key) {
    return translations[key] || key;
}

// other page logic could go here
