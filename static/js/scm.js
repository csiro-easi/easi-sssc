/**
 * Display the JSON for entry in modal popup.
 */
function show_entry_json(entry) {
    $.get(entry,
          function(data) {
              var pre = $('<script type="text/syntaxhighlighter" class="brush: javascript">').text(js_beautify(data));
              $('.api-json-modal .modal-body').append(pre);
              SyntaxHighlighter.highlight(null, pre[0]);
          },
         "script");
}
