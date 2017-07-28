def generate_confluence_graph(project, data):
	html = ""
	html += '''
	<h1>{0}</h1>
	<p>
	<ac:structured-macro ac:macro-id="f16ff7f1-2469-49cb-ad18-d9ed551fe985" ac:name="chart" ac:schema-version="1">
  	<ac:parameter ac:name="orientation">vertical</ac:parameter>
  	<ac:parameter ac:name="tables">1,2</ac:parameter>
  	<ac:parameter ac:name="subTitle">Average response times in different releases</ac:parameter>
  	<ac:parameter ac:name="title">{0}</ac:parameter>
  	<ac:parameter ac:name="type">bar</ac:parameter>
  	<ac:parameter ac:name="yLabel">Response times (ms)</ac:parameter>
 	<ac:parameter ac:name="xLabel">Release</ac:parameter>
 	<ac:parameter ac:name="width">900</ac:parameter>
  	<ac:parameter ac:name="height">500</ac:parameter>
  	<ac:rich-text-body>
    <table class="wrapped">
      <colgroup>
        <col/>
        <col/>
      </colgroup>
      <tbody>
        <tr>
          <th>Release</th>
          <th>Response times (ms)</th>
        </tr>
	'''.format(project['project_name'])
	for row in data:
		html += """
		<tr>
          <td>{0}</td>
          <td>{1}</td>
        </tr>
		""".format(row['test_name'],row['Average'])
	html += '''
		</tbody>
   		</table>
  	</ac:rich-text-body>
	</ac:structured-macro>
	</p>
	'''
	return html

