DROP TABLE IF EXISTS oligos;
CREATE TABLE oligos
(
    oligo_tube INT unsigned NOT NULL AUTO_INCREMENT PRIMARY KEY,
    oligo_name VARCHAR(150),
    sequence VARCHAR(2000),
    creator VARCHAR(25),
    creation_date DATE,
    restrixn_site VARCHAR(20),
    notes VARCHAR(500)
);
LOAD DATA LOW_PRIORITY LOCAL INFILE '/Users/nweir/Dropbox/code/denic_db/20180206_oligos_fixed.csv'
    INTO TABLE oligos
    COLUMNS TERMINATED BY ','
    LINES TERMINATED BY '\n'
    IGNORE 1 LINES
    (@dummy, oligo_tube, oligo_name, sequence, creator, notes, restrixn_site, @dummy);
