/**
 * Paste the URL for uploaded resource described by data into the text field
 * associated with target.
 */
function pasteUploadedURL(target, data) {
  // Find the text input associated with target
  var textInput = $(target).parent('span').siblings('input')[0];

  // Paste the url from data
  $(textInput).val(data['@id']);
}


$(function() {
  // Associate pasteUploadedURL as the callback for the file upload dialog.
  $('.upload-to-url').data('uploaded', pasteUploadedURL);
});
