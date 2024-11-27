import os

from functools import lru_cache
from pydantic_settings import BaseSettings

from src.utils.utils import load_yaml
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    app_name: str = "Impetus Expert Agent API"
    JWT_SECRET: str = os.getenv("JWT_SECRET")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM")
    CONFIG_PATHS_YML: str = os.getenv("CONFIG_PATHS_YML")
    API_ROOT: str = os.getenv("API_ROOT")

    def get_module_path(self, module: str):
        """Given a module of the APP, it returns its configuration. The module needs to exist
        otherwise will raise an error. APP modules are:
        - configs
        - data
        - databases
        - models
        - routes
        - schemas

        Args:
            module (str): Name of the module we want to retrieve its path.
        """
        api_root = self.API_ROOT
        if not os.path.exists(api_root):
            raise ValueError(f"The API root path {api_root} does not exist.")
        module_path = os.path.join(api_root, module)
        if not os.path.exists(module_path):
            raise ValueError(f"The API module path {module_path} does not exist.")
        return module_path

    def load_component_yml(self, yml_config_key: str):
        """Given a key of the MAIN configuration_paths.yml file, it returns the YML
        designed by the provided `yml_config_key` parameter.

        If the provided key is not inside MAIN configuration_paths.yml file, it returns an
        error.

        Args:
            yml_config_key (str): Refers to a pre-existent key from MAIN
            configuration_paths.yml file pointing into a specific component config.
        """
        configs_path = self.get_module_path("configs")
        base_conf_path = os.path.join(configs_path, self.CONFIG_PATHS_YML)
        base_conf_yml = load_yaml(base_conf_path)

        if yml_config_key not in base_conf_yml:
            raise ValueError(
                f"The MAIN key {yml_config_key} does not exist in `configuration_paths.yml` file."
            )

        component_conf_path = os.path.join(configs_path, base_conf_yml[yml_config_key])
        component_yml = load_yaml(component_conf_path)
        component_yml = {k: self.__handle_paths(v) for k, v in component_yml.items()}
        return component_yml

    def __handle_paths(self, value: str):
        potential_path = self.API_ROOT + os.path.sep + str(value)
        return value if not os.path.exists(potential_path) else potential_path


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
