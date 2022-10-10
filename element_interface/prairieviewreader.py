import pathlib
import glob
import xml.etree.ElementTree as ET
import numpy as np
from datetime import datetime


def get_pv_metadata(pvtiffile):
    """Extract metadata for calcium imaging scans generated by Bruker Systems PrairieView acquisition software.

    The PrairieView software generates one .ome.tif imaging file per frame acquired. The metadata for all frames is contained one .xml file. This function locates the .xml file and generates a dictionary necessary to populate the DataJoint ScanInfo and Field tables.

    PrairieView works with resonance scanners with a single field.

    PrairieView does not support bidirectional x and y scanning.

    ROI information is not contained in the .xml file.

    All images generated using PrairieView have square dimensions (e.g. 512x512).


    Args:
        pvtiffile: An absolute path to the .ome.tif image file.

    Raises:
        FileNotFoundError: No .xml file containing information about the acquired scan was found at path in parent directory at `pvtiffile`.

    Returns:
        metainfo: A dict mapping keys to corresponding metadata values fetched from the .xml file.
    """

    xml_files = pathlib.Path(pvtiffile).parent.glob("*.xml") # May return multiple xml files. Only need one that contains scan metadata.

    for xml_file in xml_files :
        tree = ET.parse(xml_file)
        root = tree.getroot()
        if root.find(".//Sequence"):
            break
    else:
        raise FileNotFoundError(
            f"No PrarieView metadata XML file found at {pvtiffile.parent}"
        )

    bidirectional_scan = False  # Does not support bidirectional

    nfields = 1  # Always contains 1 field

    # Get all channels and find unique values
    channel_list = []
    channels = root.iterfind(".//Sequence/Frame/File/[@channel]")
    for channel in channels:
        channel_list.append(int(channel.attrib.get("channel")))
    nchannels = np.unique(channel_list).shape[0]

    # One "Frame" per depth. Gets number of frames in first sequence
    planes_list = []
    planes = root.findall(".//Sequence/[@cycle='1']/Frame")
    for plane in planes:
        planes_list.append(int(plane.attrib.get("index")))
    ndepths = np.unique(planes_list).shape[0]

    # Total frames are displayed as number of "cycles"
    nframes = int(root.findall(".//Sequence")[-1].attrib.get("cycle"))

    roi = 1

    x_coordinate = float(
        root.find(
            ".//PVStateValue/[@key='currentScanCenter']/IndexedValue/[@index='XAxis']"
        ).attrib.get("value")
    )
    y_coordinate = float(
        root.find(
            ".//PVStateValue/[@key='currentScanCenter']/IndexedValue/[@index='YAxis']"
        ).attrib.get("value")
    )
    z_coordinate = float(
        root.find(
            ".//PVStateValue/[@key='positionCurrent']/SubindexedValues/[@index='ZAxis']/SubindexedValue/[@subindex='0']"
        ).attrib.get("value")
    )

    framerate = np.divide(
        1,
        float(
            root.findall('.//PVStateValue/[@key="framePeriod"]')[0].attrib.get("value")
        ),
    )  # rate = 1/framePeriod

    usec_per_line = (
        float(
            root.findall(".//PVStateValue/[@key='scanLinePeriod']")[0].attrib.get(
                "value"
            )
        )
        * 1e6
    )  # Convert from seconds to microseconds

    scan_datetime = datetime.strptime(root.attrib.get("date"), "%m/%d/%Y %I:%M:%S %p")

    total_duration = float(
        root.findall(".//Sequence/Frame")[-1].attrib.get("relativeTime")
    )

    bidirectionalZ = bool(root.find(".//Sequence").attrib.get("bidirectionalZ"))

    px_height = int(
        root.findall(".//PVStateValue/[@key='pixelsPerLine']")[0].attrib.get("value")
    )
    px_width = px_height  # All PrairieView-acquired images have square dimensions (512 x 512; 1024 x 1024)

    um_per_pixel = float(
        root.find(
            ".//PVStateValue/[@key='micronsPerPixel']/IndexedValue/[@index='XAxis']"
        ).attrib.get("value")
    )
    um_height = float(px_height) * um_per_pixel
    um_width = (
        um_height  # All PrairieView-acquired images have square dimensions (512 x 512)
    )

    x_field = x_coordinate  # X-coordinates do not change during scan
    y_field = y_coordinate  # Y-coordinates do not change during scan
    z_min = root.findall(
        ".//Sequence/[@cycle='1']/Frame/PVStateShard/PVStateValue/[@key='positionCurrent']/SubindexedValues/SubindexedValue/[@subindex='0']"
    )[0].attrib.get("value")
    z_max = root.findall(
        ".//Sequence/[@cycle='1']/Frame/PVStateShard/PVStateValue/[@key='positionCurrent']/SubindexedValues/SubindexedValue/[@subindex='0']"
    )[-1].attrib.get("value")
    z_step = root.find(
        ".//PVStateShard/PVStateValue/[@key='micronsPerPixel']/IndexedValue/[@index='ZAxis']"
    ).attrib.get("value")
    z_fields = np.arange(z_min, z_max + 1, z_step)
    assert z_fields.shape[0] == ndepths

    metainfo = dict(
        num_fields=nfields,
        num_channels=nchannels,
        num_planes=ndepths,
        num_frames=nframes,
        num_rois=roi,
        x_pos=x_coordinate,
        y_pos=y_coordinate,
        z_pos=z_coordinate,
        frame_rate=framerate,
        bidirectional=bidirectional_scan,
        bidirectional_z=bidirectionalZ,
        scan_datetime=scan_datetime,
        usecs_per_line=usec_per_line,
        scan_duration=total_duration,
        height_in_pixels=px_height,
        width_in_pixels=px_width,
        height_in_um=um_height,
        width_in_um=um_width,
        fieldX=x_field,
        fieldY=y_field,
        fieldZ=z_fields,
    )

    return metainfo
