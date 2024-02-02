#functions map
fm = {
	#remap non renamed
	**{v:v for v in [
		"__construct",
		"__destruct",
		"__autoload",
		"close",
		"escape",

		# includes/geo.php
		"cnstats_Geo",

		# geo/cngeoip5/CNGeoIP.php
		"get_place_by_ip",
		"get_description_by_ip",
		"get_description_by_place",
		"is_valid",
		"get_error",

		# geo/ip2location/ip2location.class.php
		"ip2location",
		"destructor",
		"error",
		"getVersion",
		"open",
		"bigEndianUnpack",
		"readBinary",
		"read8",
		"read32",
		"read128",
		"readString",
		"readFloat",
		"bytes2Int",
		"isIPv4",
		"isIPv6",
		"ipv6ToLong",
		"notSupported",
		"invalidIPAddress",
		"invalidIPv6Address",
		"getRecord",
		"getRecordV6",
		"getCountryShort",
		"getCountryLong",
		"getRegion",
		"getCity",
		"getIsp",
		"getLatitude",
		"getLongitude",
		"getZipCode",
		"getDomain",
		"getTimeZone",
		"getNetSpeed",
		"getIddCode",
		"getAreaCode",
		"getWeatherStationCode",
		"getWeatherStationName",
		"getAll"
	]},

	"_0e5ea304": "set_language",
	"_7ad9fffc": "mail_subject_rfc_helper",
	"_f43c4f66": "html_end",
	"_5dddbc71": "db_error"
}

#variables map
vm = {
	#remap non renamed
	**{"$"+v:"$"+v for v in [
		"_COOKIE",
		"_SERVER",
		"_POST",
		"_GET"
	]},

	"$_f26ec1be": "$version_str",
	"$_5ecd97c9": "$version_id",
	"$_39409301": "$version_type",
	"$_e27fb514": "$name_with_version",
	"$_085742f1": "$styled_product_info",
	"$_704910a1": "$html_charsets",
	"$_bfa4ce15": "$charset",
	"$_cf2713fd": "$DB_HOST",
	"$_8d93d649": "$DB_USER",
	"$_5a6dd5f6": "$DB_SERVER",
	"$_be3269d8": "$DB_NAME",
	"$_5dddbc71": "$db_error_description",
	"$_27c0e1e9": "$db_error_code",
	"$_24bdb5eb": "$db_error_text",
}
