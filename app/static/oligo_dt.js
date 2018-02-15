$(document).ready(function() {
    var table = $('#search_results').DataTable( {
        lengthChange: false,
        buttons: [ 'copy', 'excel', 'csv', 'colvis' ]
    } );
 
    table.buttons().container()
        .appendTo( '#example_wrapper .col-sm-6:eq(0)' );
} );
