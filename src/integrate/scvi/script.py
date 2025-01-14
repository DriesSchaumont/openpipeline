from scanpy._utils import check_nonnegative_integers
import mudata
import scvi

### VIASH START
par = {
    "input": "resources_test/pbmc_1k_protein_v3/pbmc_1k_protein_v3_mms.h5mu",
    "modality": "rna",
    "input_layer": None,
    "obs_batch": "sample_id",
    "var_input": None,
    "output": "foo.h5mu",
    "obsm_output": "X_scvi_integrated",
    "early_stopping": True,
    "early_stopping_monitor": "elbo_validation",
    "early_stopping_patience": 45,
    "early_stopping_min_delta": 0,
    "reduce_lr_on_plateau": True,
    "lr_factor": 0.6,
    "lr_patience": 30,
    "max_epochs": 500,
    "n_obs_min_count": 10,
    "n_var_min_count": 10,
    "model_output": "test/",
    "output_compression": "gzip",
    }

meta = {
    "resources_dir": 'src/integrate/scvi'
}
### VIASH END

import sys
sys.path.append(meta['resources_dir'])
from subset_vars import subset_vars

#TODO: optionally, move to qa
# https://github.com/openpipelines-bio/openpipeline/issues/435
def check_validity_anndata(adata, layer, obs_batch,
                           n_obs_min_count, n_var_min_count):
    assert check_nonnegative_integers(
        adata.layers[layer] if layer else adata.X
    ), f"Make sure input adata contains raw_counts"

    assert len(set(adata.var_names)) == len(
        adata.var_names
    ), f"Dataset contains multiple genes with same gene name."

    # Ensure every obs_batch category has sufficient observations
    assert min(adata.obs[[obs_batch]].value_counts()) > n_obs_min_count, \
        f"Anndata has fewer than {n_obs_min_count} cells."

    assert adata.n_vars > n_var_min_count, \
        f"Anndata has fewer than {n_var_min_count} genes."



def main():
    mdata = mudata.read(par["input"].strip())
    adata = mdata.mod[par['modality']]

    if par['var_input']:
        # Subset to HVG
        adata = subset_vars(adata, subset_col=par["var_input"])

    check_validity_anndata(
        adata, par['input_layer'], par['obs_batch'],
        par["n_obs_min_count"], par["n_var_min_count"]
        )
    # Set up the data
    scvi.model.SCVI.setup_anndata(
        adata,
        batch_key=par['obs_batch'],
        layer=par['input_layer']
    )

    # Set up the model
    vae_uns = scvi.model.SCVI(
        adata,
        n_hidden=128, #this is the default
        n_latent=30,
        n_layers=2,
        dropout_rate=0.1, #this is the default
        dispersion='gene', #this is the default
        gene_likelihood='nb',
        use_layer_norm='both',
        use_batch_norm="none",
        encode_covariates=True, #Parameterization for better scArches performance -> maybe don't use this always?
        deeply_inject_covariates=False, #Parameterization for better scArches performance -> maybe don't use this always?
        use_observed_lib_size=False, #When size_factors are not passed
    )

    plan_kwargs = {
        "reduce_lr_on_plateau": par['reduce_lr_on_plateau'],
        "lr_patience": par['lr_patience'],
        "lr_factor": par['lr_factor'],
    }


    # Train the model
    vae_uns.train(
        max_epochs = par['max_epochs'],
        early_stopping=par['early_stopping'],
        early_stopping_monitor=par['early_stopping_monitor'],
        early_stopping_patience=par['early_stopping_patience'],
        early_stopping_min_delta=par['early_stopping_min_delta'],
        plan_kwargs=plan_kwargs,
        check_val_every_n_epoch=1,
        accelerator="auto",
    )
    #Note: train_size=1.0 should give better results, but then can't do early_stopping on validation set

    # Get the latent output
    adata.obsm[par['obsm_output']] = vae_uns.get_latent_representation()

    mdata.mod[par['modality']] = adata
    mdata.write_h5mu(par['output'].strip(), compression=par["output_compression"])
    if par["model_output"]:
        vae_uns.save(par["model_output"], overwrite=True)

if __name__ == "__main__":
    main()
