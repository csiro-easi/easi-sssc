$(function() {
  /*
   * Stash the related target (button that fired the dialog) on the form, so we
   * can inspect it for a callback function after the file is uploaded.
   */
  $('#uploadFileDialog').on('show.bs.modal', function(event) {
    var button = $(event.relatedTarget);
    $(this).find('form.upload-form').data('upload-target', button[0]);
  });


  /*
   * Handle file upload dialog submission.
   */
  $('#uploadFileDialog .upload-form').submit(function(event) {
    // Stop form being submitted normally
    event.preventDefault();

    // Get the URL from the form's action attribute
    var $form = $(this),
        url = $form.attr('action');

    // Use FormData to include the file to upload
    var data = new FormData($form[0]);

    // POST the data
    var request = $.ajax({
      url: url,
      method: 'POST',
      data: data,
      contentType: false,
      processData: false,
      dataType: 'json'
    });

    // Close the dialog and report the results once the request has finished.
    request.done(function(data) {
      // Hide the dialog.
      $('#uploadFileDialog').modal('hide');

      // Inspect the element that triggered the dialog. If it has a callback
      // registered then call that function, passing the triggering element and
      // the data returned from the upload request.
      var target = $form.data('upload-target');
      var callback = $(target).data('uploaded');
      if (callback) {
        callback(target, data);
      }
      else {
        // Load the user profile page
        location.assign(data.user);
      }
    });
  });

});

