// $(document).on('submit', '[id^=deanery-pay-submit]', function (e) {
//     e.preventDefault();

//     let student_id = $(this).data('id');
//     let url = $(this).attr('action');
//     let student = $(`#credit-${student_id}`);
//     const csrftoken = Cookies.get('csrftoken');

//     $.ajax({
//         headers: { "X-CSRFToken": csrftoken },
//         contentType: 'application/json; charset=utf-8',
//         url: url,
//         method: 'POST',
//         data: JSON.stringify({
//             credit_id: credit_id
//         }),
//         success: function (response) {
//             $(`#PayModal-close-button${student_id}`).click();

//             if (response.success) {
//                 credit.find('td#pay-submit').remove();
//                 credit.find('td#status').html(`<span class="badge bg-label-info">${gettext("Оплатил")}</span>`)
//             }

//         },
//         error: function (xhr, status, error) {
//             console.log('Error:', error);
//         }
//     });
// })