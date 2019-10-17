var csrf = $('#page-data').data('csrf');
var test = new Test(csrf);
var testReport = new TestReport(test);
testReport.init();
window.dispatchEvent(new Event('resize'))
