 $( document ).ready(function() {

          $(document).on("click", ".openModal", function () {
            var myUserName = $(this).data('username');
            var myUserGroup = $(this).data('group');
            $("#myModalLabel").text("Edit " + myUserGroup + " '" + myUserName + "'" );
            $("#username").val(myUserName);
            $("#groupname").val(myUserGroup);

            $('input:radio[name=editOption][value=password]').click();
          });

          $('#btnSave').click(function() {
            $('#frmEditUser').submit();
          });

          $('input[name="editOption"]').click(function(){
            if($(this).attr("value")=="password"){
                $(".password").show();
                $(".modal-body #inPass").val("");
                $(".group").hide();
                $(".erase").hide();
            }
            if($(this).attr("value")=="group"){
                $("#selGroup option").each(function() { this.selected = (this.text == $("#groupname").val()); });
                $(".password").hide();
                $(".group").show();
                $(".erase").hide();
            }
            if($(this).attr("value")=="erase"){
                $(".password").hide();
                $(".group").hide();
                $(".erase").show();
            }
          });
        });

