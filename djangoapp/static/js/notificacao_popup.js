function showNotification(title, message, type='info', icon='icon-bell') {
    $.notify({
        icon: icon,
        title: title,
        message: message,
    }, {
        type: type,
        placement: {
            from: "bottom",
            align: "right"
        },
        time: 1000,
    });
}

function showMessagesAsNotifications() {
    // Obtemos os dados das notificações a partir de atributos HTML
    var messages = $('#notification-messages').data('messages') || [];

    // Mostrar cada mensagem como uma notificação
    messages.forEach(function(msg) {
        showNotification('', msg, 'info', 'icon-bell');
    });
}


$(document).ready(function() {
    showMessagesAsNotifications();
});
