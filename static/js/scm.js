/**
 * Display code with syntax highlighting.
 *
 * Retrieves the code text from url, optionally passes it to tfn if supplied for
 * transformation, wraps it in a syntaxhighlighter <script> element with the
 * appropriate brush and appends that to the selected element.
 *
 * url -- URL to retrieve content from
 * selector -- jquery selector to find element for content
 * brush -- syntaxhighlighter brush to use
 * tfn -- optional function to transform the data for
 */
function show_code(url, selector, brush) {
  // Capture the optional function arg.
  var argfn = arguments[3];

  // Default tfn applies argfn if supplied, then escapes characters for display.
  var tfn = function(text) {
    var newtext = text;

    if (argfn) {
      newtext = argfn(newtext);
    }

    return newtext.replace("<", "&lt;");
  };

  $.get(url,
        function(data) {
          var text = tfn(data);

          var code = $('<pre type="syntaxhighlighter" class="brush: ' + brush + '">')
              .text(text);
          $(selector).append(code);
          SyntaxHighlighter.highlight(null, code[0]);
        },
        "text");
}

/**
 * Display the JSON for entry in modal popup.
 */
function show_entry_json(entry) {
  show_code(entry, '.api-json-modal .modal-body', "javascript", js_beautify);
}

/**
 * Display the template source in a solution.
 */
function show_solution_template(template) {
  show_code(template, ".template-source", "python");
}

function show_toolbox_template(url) {
  show_code(url, ".template-source", "ruby");
}

/**
 * Confirm publish actions before continuing.
 */
$(function() {
  $('.confirm-publish').click(function() {
    return confirm('Are you sure you want to publish this entry?');
  });
});
