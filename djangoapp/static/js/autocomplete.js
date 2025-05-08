function initSelect2Ajax(id, url, placeholderText = 'Selecione uma opção') {
    $('#' + id).select2({
        placeholder: placeholderText,
        ajax: {
            url: url,
            dataType: 'json',
            delay: 250,
            data: function (params) {
                return {
                    q: params.term
                };
            },
            processResults: function (data) {
                return {
                    results: data.results
                };
            },
            cache: true
        },
        width: 'resolve'
    }).on('select2:open', function () {
        $('.select2-container--open .select2-search__field').addClass('form-control');
    });

}
