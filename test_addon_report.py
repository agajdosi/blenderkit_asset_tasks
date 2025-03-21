"""Script to generate comment from the test results and post the comment under the add-on on BlenderKit.com.
Results are expected to be at: temp/blender-{x.y}/test_addon_results.json
"""

from collections import OrderedDict
from pathlib import Path
from os import environ
import json

from blenderkit_server_utils import api_nice


def read_result_files() -> OrderedDict[str, dict]:
  temp = Path("temp")
  results = OrderedDict()
  for entry in temp.iterdir():
    if entry.is_file():
      continue

    for file in entry.iterdir():
      json_data = json.loads(file.read_text())
      results[entry.name] = json_data

  return results


def generate_comment(results: OrderedDict[str, dict]) -> str:
  if len(results) == 0:
    raise Exception("Results are expected to be not empty")
  comment = "We have automatically tested your add-on. Below are the results:"
  all_ok = True
  for rkey, release in results.items():
    release_ok = True
    message = ""
    for tkey, test in release.items():
      if test == "": #empty error -> test OK
        continue
      release_ok = False
      all_ok = False
      message += f"\n- test '{tkey}' failed: {test}"
    if release_ok:
      message = "OK"
    else:
      message = f"FAIL{message}"
    comment += f"\n***\n**{rkey}**: {message}"

  if not all_ok:
    comment += "\n***\nSome tests has failed. Please check your add-on in the failed versions of Blender. It is possible there is a problem."

  return comment


results = read_result_files()
comment = generate_comment(results)
print(f"comment generated:\n{comment}")

api_nice.create_comment(
  comment=comment,
  asset_base_id=environ.get('ASSET_BASE_ID', ''),
  api_key=environ.get('TEXTYBOT_API_KEY', environ.get('BLENDERKIT_API_KEY', '')), # prefer KEY for account of specialized commenting bot
  server_url=environ.get('BLENDERKIT_SERVER', '')
)
print(f"comment uploaded")
