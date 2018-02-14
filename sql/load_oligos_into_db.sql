LOAD DATA LOW_PRIORITY LOCAL INFILE '/Users/nweir/Dropbox/code/denic_db/20180206_oligos_fixed.csv'
    INTO TABLE oligos
    COLUMNS TERMINATED BY ','
    LINES TERMINATED BY '\n'
    IGNORE 1 LINES
    (@dummy, oligo_tube, oligo_name, sequence, creator_str, notes, restrixn_site, @dummy);
