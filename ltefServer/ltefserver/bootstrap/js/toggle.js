/*
Button Toggle hides and shows the side navigation 
*/
$(document).ready(function(){
    $("button.toggle").click(function(){
        $("#wrapper").toggleClass("toggled");
    });
  ;
});


