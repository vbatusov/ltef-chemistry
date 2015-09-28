$( document ).ready(function() {
      // First button behaviour
      var link =   $("#result").attr("src")
      $('#result').load( link + ' #svg_data');
      // First button behaviour
      $("#getButton").click(function() {
          $('#result').load( link + ' #svg_data');
       });
});
