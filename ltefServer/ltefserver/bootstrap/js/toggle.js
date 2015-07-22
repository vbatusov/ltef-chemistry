/*
Button Toggle hides and shows the side navigation 
*/
$(document).ready(function(){
    $("button.toggle").click(function(){
        $("#wrapper").toggleClass("toggled");
    });


    $('#dataTable').dataTable( {
    } );

function toggleFolder(e) {
    $(e.target)
        .prev('.panel-heading')
        .find("i.indicator")
        .toggleClass('glyphicon-folder-open glyphicon-folder-close');
}
$('#expandable_folders').on('hidden.bs.collapse', toggleFolder);
$('#expandable_folders').on('shown.bs.collapse', toggleFolder);


});


