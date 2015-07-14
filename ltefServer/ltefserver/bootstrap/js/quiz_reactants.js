      $( document ).ready(function() {

        $(".molecule").data("selected", 0)

        $(".molecule").click(function(){
          if ($(this).data("selected") == 0) {
            $(this).css({"border-color":"#ff8888"});
            $(this).data("selected", 1)
          }
          else {
            $(this).css({"border-color":"#ffffff"});
            $(this).data("selected", 0)
          }

          var x = [];
          $('.molecule').each(function(i, obj) {
            //alert ("Molecule " + i)
            if ($(this).data("selected") == 1) {
              //alert ("Is selected")
              x.push(obj.id)
            }
          });
          //alert(x)
          $("#answerField").val(x);

        });
      });

