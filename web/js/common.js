function parseTables() {
	$('.odds_table').dynatable({
		table: {
		   defaultColumnIdStyle: 'trimDash'
		}
	});
}

$(document).ready(function(){
		parseTables();
});
