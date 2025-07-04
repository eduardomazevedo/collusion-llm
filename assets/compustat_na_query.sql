SELECT
    comp_na_daily_all.funda.costat,
    comp_na_daily_all.funda.curcd,
    comp_na_daily_all.funda.datafmt,
    comp_na_daily_all.funda.indfmt,
    comp_na_daily_all.funda.consol,
    comp_na_daily_all.funda.gvkey,
    comp_na_daily_all.funda.datadate,
    comp_na_daily_all.funda.conm,
    id_table.ggroup,
    id_table.gind,
    id_table.gsector,
    id_table.gsubind,
    id_table.naics,
    id_table.sic,
    id_table.spcindcd,
    comp_na_daily_all.funda.fyear,
    comp_na_daily_all.funda.emp,
    comp_na_daily_all.funda.mkvalt,
    comp_na_daily_all.funda.naicsh,
    comp_na_daily_all.funda.sich

FROM comp_na_daily_all.funda
INNER JOIN (
    SELECT
        gvkey,
        ggroup,
        gind,
        gsector,
        gsubind,
        naics,
        sic,
        spcindcd
    FROM comp_na_daily_all.company
    WHERE comp_na_daily_all.company.gvkey IN (
        {GVKEY_LIST}  -- Replace with actual list of gvkeys
    )
) AS id_table 

ON comp_na_daily_all.funda.gvkey = id_table.gvkey

WHERE comp_na_daily_all.funda.datadate ("comp_na_daily_all"."funda"."consol" = ANY (ARRAY['C']) AND "comp_na_daily_all"."funda"."indfmt" = ANY (ARRAY['INDL','FS']) AND "comp_na_daily_all"."funda"."datafmt" = ANY (ARRAY['STD']) AND "comp_na_daily_all"."funda"."curcd" = ANY (ARRAY['USD','CAD']) AND "comp_na_daily_all"."funda"."costat" = ANY (ARRAY['A','I']))
