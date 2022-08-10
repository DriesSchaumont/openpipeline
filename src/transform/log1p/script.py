import scanpy as sc
import muon as mu
import logging
from sys import stdout

## VIASH START
par = {
    "input": "resources_test/pbmc_1k_protein_v3/pbmc_1k_protein_v3_filtered_feature_bc_matrix.h5mu",
    "output": "output.h5mu",
    "base": None,
    "modality": ["rna"],
}
meta = {"functionality_name": "lognorm"}
## VIASH END

logger = logging.getLogger()
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler(stdout)
logFormatter = logging.Formatter("%(asctime)s %(levelname)-8s %(message)s")
console_handler.setFormatter(logFormatter)
logger.addHandler(console_handler)

logger.info("Reading input mudata")
mdata = mu.read_h5mu(par["input"])
mdata.var_names_make_unique()

for mod in par["modality"]:
    logger.info("Performing log transformation on modality %s", mod)
    sc.pp.log1p(mdata.mod[mod], base=par["base"])

logger.info("Writing to file %s", par["output"])
mdata.write(filename=par["output"])
