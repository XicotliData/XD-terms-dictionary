""" library to build XicotliData dictionary static site

this module exposes the build process for the XicotliData
dictionary static site.
"""
import importlib.resources
import logging
from pathlib import Path
from shutil import copytree
import sys
from typing import BinaryIO, Union
import click
from jinja2 import Environment, PackageLoader, select_autoescape
import pandas as pd


SCRIPT_TASKS = ['build', 'validate']

def configure_logging(verbosity:int) -> None:
    """configure verbosity level"""
    log_level = max(10, 30-10 * verbosity)
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stdout,
        level=log_level)

def get_values_of(of_id: int, values_df: pd.DataFrame) -> list:
    """ return a list with the values associated to and observation field """
    return values_df.loc[values_df["observationFieldID"] == of_id,
                         ["values", "url"]].to_dict(orient="records")

def process_xd_dict(xd_dict_path: BinaryIO) -> pd.DataFrame:
    """ proccess a xd dictionary file """
    values_obs_fields_data = (pd.read_excel(xd_dict_path, sheet_name=1)
                              .rename(columns={'Unnamed: 4': 'url'})
                              .loc[:, ["observationFieldID", "values", "url"]]
                             )
    obs_fields_data = (pd.read_excel(xd_dict_path, sheet_name=0)
                       .rename(columns={
                           'naturalistaFilteredValues': 'url',
                           "ObservationField (Name)": "of_name",
                           "ObservationField ID (iNat)": "of_id",
                           "Observación / Descripción del campo": "description"
                        })
                       .loc[:,
                            ["observationFieldID", "of_name", "of_id", "url", "description"]]
                       .assign(of_values = lambda x: x["observationFieldID"].apply(get_values_of,
                                                                                   args=(values_obs_fields_data,)))
                      )

    obs_fields_data.loc[obs_fields_data['of_values'].apply(len) == 0,
                        "of_values"] = None

    return obs_fields_data.where(obs_fields_data.notnull(), None)

@click.command()
@click.option('--task', required=True,
              type=click.Choice(SCRIPT_TASKS),
              help="choose xd dictionary tasks")
@click.option('-v', '--verbose', count=True, help="increase verbosity level")
@click.option('--build_dir',
              type=click.Path(file_okay=False, path_type=Path),
              help="where build files are saved")
@click.argument('xd_file', type=click.File('rb'))
def main(
        verbose: int,
        task: str,
        xd_file: BinaryIO,
        build_dir: Union[Path, None] = None
        ) -> None:
    configure_logging(verbose)
    logging.info(f'processing {xd_file.name}')
    if task == "validate":
        click.echo("option doesn't yet implemented")
        return
    xd_data = process_xd_dict(xd_file)

    env = Environment(
            loader=PackageLoader('xd_dictionary'))

    terms_tmpl = env.get_template('terms.html.jinja')

    if not build_dir:
        click.echo(terms_tmpl.render(terms=xd_data.to_dict(orient="records")))
        return
    static_path = importlib.resources.path("xd_dictionary.templates", "static")
    logging.debug(f"static path: {static_path}")

    build_dir.mkdir(exist_ok=True)
    copytree(str(static_path), build_dir / "static", dirs_exist_ok=True)
    fn = build_dir / "index.html"
    with fn.open('w') as f:
        f.write(terms_tmpl.render(terms=xd_data.to_dict(orient="records"), output_dir=True))

if __name__ == "__main__":
    pass
