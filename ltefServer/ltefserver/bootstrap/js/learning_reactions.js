$( document ).ready(function() {
      // First button behaviour
      $("#getButton").click(function() {
      $("#instanceImage").attr("src", $("#instanceImage").attr("src").split('?')[0] + "?" + new Date().getTime());
      var molDiv = "<div class='blah' style='background-image: url(${request.static_url('ltefserver:static/img/mol2.png')});'></div>";
      $("#molSpan").append(molDiv);
       });
});
