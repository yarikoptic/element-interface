import nd2
import tifffile


def nd2totif(nd2_file):
    """
    Convert Nikon .nd2 file to .tif file.

    file: str
        Path to the .nd2 file.
    """
    f = nd2.ND2File(nd2_file)
    tif_file = nd2_file[:-3] + 'tif'
    tifffile.imwrite(tif_file, f.asarray(), imagej=True)
