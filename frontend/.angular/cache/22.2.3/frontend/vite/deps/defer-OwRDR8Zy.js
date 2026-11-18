import { ql as Observable } from "./core-B4euoBVh.js";
import { t as innerFrom } from "./innerFrom-Dwddq0Ia.js";
//#region node_modules/rxjs/dist/esm5/internal/observable/defer.js
function defer(observableFactory) {
	return new Observable(function(subscriber) {
		innerFrom(observableFactory()).subscribe(subscriber);
	});
}
//#endregion
export { defer as t };
