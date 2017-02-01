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
  $.get(url,
        function(data) {
          var text = data;
          if (arguments.length > 3) {
            text = arguments[3](text);
          }

          var code = $('<script type="text/syntaxhighlighter" class="brush: ' + brush + '">')
              .text(text);
          $(selector).append(code);
          SyntaxHighlighter.highlight(null, code[0]);
        },
        "script");
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
