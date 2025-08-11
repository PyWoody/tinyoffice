import enum
import io
import os
import tempfile
import zipfile

from collections import namedtuple
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from PIL import Image

try:
    from rich import print
except ModuleNotFoundError:
    pass


CompressionRecord = namedtuple(
    'CompressionRecord',
    [
        'filename',
        'errors',
        'num_images_compressed',
        'num_images_converted',
        'num_images_skipped',
        'start_size',
        'compressed_size',
    ]
)


class Verbosity(enum.Enum):
    NONE = enum.auto()
    LOW = enum.auto()
    NORMAL = enum.auto()
    HIGH = enum.auto()


def walk(
    cwd,
    *,
    types=None,
    overwrite=False,
    output=None,
    convert=False,
    verbosity=Verbosity.NORMAL,
    image_extensions=None,
    jpeg_quality=75,
    tiff_quality=75,
    optimize=True,
):
    """
    Recursively iterates over the files starting from the cwd
    and attempts to convert and/or compress them if they match
    the listed file types

    Args:
        cwd: Path to directory to start from

    Kwargs:
        types: Office filetype extension(s) to use.
               Accepts either a str or list-like object.
               Default is None which will use .docx, .pptx, and .xlsx
        output: Location root to add save the compressed files.
                Default is None which will use the location where
                the script was called
        overwrite: Overwrite if output exists. Default is False
        convert: Convert TIFFs to JPEGs. Default is False
        verbosity: Verbosity level. Default is Verbosity.NORMAL
        image_extensions: Supported image extensions. Default is None which
                          will use only the supported extensions that
                          can be OPENed and SAVEd by PIL on your machine.
        jpeg_quality: Defaults to 75, which is PIL's default quality value
        tiff_quality: Defaults to 75, which is PIL's default quality value
        optimize: Defaults to True.
                  If true, an optimization pass will be attempted
                  Will be applied to JPEG and PNGs only
    """
    if types is None:
        types = {'.docx', '.pptx', '.xlsx'}
    else:
        if isinstance(types, str):
            types = {types}
        else:
            types = {i for i in types}
    if output is None:
        output = os.getcwd()
    else:
        if os.path.splitext(output)[1]:
            # A file but it may not exist so you can't .isfile it
            output = os.path.dirname(output)
        else:
            output = os.path.realpath(output)
        os.makedirs(output, exist_ok=True)

    if verbosity is not Verbosity.NONE:
        printer_callback = partial(printer, verbosity=verbosity)
        output_record = {
            'compressed_files': [],
            'errors': [],
            'image_errors': [],
            'images_total': 0,
            'images_compressed': 0,
            'images_skipped': 0,
            'images_converted': 0,
            'total_bytes': 0,
            'total_bytes_compressed': 0,
        }
        totaler_callback = partial(totaler, output_record)
    if image_extensions is None:
        registered_extensions = Image.registered_extensions()
        image_extensions = {
            ext for ext, func in registered_extensions.items()
            if func in Image.SAVE
            if func in Image.OPEN
        }
    with ProcessPoolExecutor() as executor:
        try:
            for root, dirs, files in os.walk(cwd):
                if output in root:
                    continue
                outpath_created = False
                for f in files:
                    if os.path.splitext(f)[1].lower() in types:
                        fpath = os.path.join(root, f)
                        outpath = os.path.join(
                            output, os.path.relpath(root, start=cwd), f
                        )
                        if overwrite or not os.path.isfile(outpath):
                            if not outpath_created:
                                os.makedirs(
                                    os.path.dirname(outpath), exist_ok=True
                                )
                                outpath_created = True
                            future = executor.submit(
                                process,
                                fpath,
                                output=outpath,
                                convert=convert,
                                image_extensions=image_extensions,
                                jpeg_quality=jpeg_quality,
                                tiff_quality=tiff_quality,
                                optimize=optimize,
                            )
                            if verbosity is not Verbosity.NONE:
                                future.add_done_callback(totaler_callback)
                                future.add_done_callback(printer_callback)
        except KeyboardInterrupt:
            print('Shutting down executor pool...')
            executor.shutdown(cancel_futures=True)
    if verbosity is not Verbosity.NONE:
        print_total(output_record, verbosity)


def listdir(
    cwd,
    *,
    types=None,
    overwrite=False,
    output=None,
    convert=False,
    verbosity=Verbosity.NORMAL,
    image_extensions=None,
    jpeg_quality=75,
    tiff_quality=75,
    optimize=True,
):
    """
    Iterates over the files in the directory and attempts to convert
    and/or compress them if they match the listed file types

    Args:
        cwd: Path to directory to use

    Kwargs:
        types: Office filetype extension(s) to use.
               Accepts either a str or list-like object.
               Default is None which will use .docx, .pptx, and .xlsx
        overwrite: Overwrite if output exists. Default is False
        convert: Convert TIFFs to JPEGs. Default is False
        verbosity: Verbosity level. Default is Verbosity.NORMAL
        image_extensions: Supported image extensions. Deafult is None which
                          will use only the supported extensions that
                          can be OPENed and SAVEd by PIL on your machine.
        jpeg_quality: Defaults to 75, which is PIL's default quality value
        tiff_quality: Defaults to 75, which is PIL's default quality value
        optimize: Defaults to True.
                  If true, an optimization pass will be attempted
                  Will be applied to JPEG and PNGs only
    """
    if types is None:
        types = {'.docx', '.pptx', '.xlsx'}
    else:
        if isinstance(types, str):
            types = {types}
        else:
            types = {i for i in types}
    if output is None:
        output = os.getcwd()
    else:
        if os.path.splitext(output)[1]:
            # A file but it may not exist so you can't .isfile it
            output = os.path.dirname(output)
        else:
            output = os.path.realpath(output)
        os.makedirs(output, exist_ok=True)

    if verbosity is not Verbosity.NONE:
        printer_callback = partial(printer, verbosity=verbosity)
        output_record = {
            'compressed_files': [],
            'errors': [],
            'image_errors': [],
            'images_total': 0,
            'images_compressed': 0,
            'images_skipped': 0,
            'images_converted': 0,
            'total_bytes': 0,
            'total_bytes_compressed': 0,
        }
        totaler_callback = partial(totaler, output_record)
    if image_extensions is None:
        registered_extensions = Image.registered_extensions()
        image_extensions = {
            ext for ext, func in registered_extensions.items()
            if func in Image.SAVE
            if func in Image.OPEN
        }
    with ProcessPoolExecutor() as executor:
        try:
            for item in os.listdir(cwd):
                fpath = os.path.join(cwd, item)
                if os.path.isfile(fpath):
                    if os.path.splitext(fpath)[1].lower() in types:
                        outpath = os.path.join(output, item)
                        if overwrite or not os.path.isfile(outpath):
                            future = executor.submit(
                                process,
                                fpath,
                                output=outpath,
                                convert=convert,
                                image_extensions=image_extensions,
                                jpeg_quality=jpeg_quality,
                                tiff_quality=tiff_quality,
                                optimize=optimize,
                            )
                            if verbosity is not Verbosity.NONE:
                                future.add_done_callback(totaler_callback)
                                future.add_done_callback(printer_callback)
        except KeyboardInterrupt:
            print('Shutting down executor pool...')
            executor.shutdown(cancel_futures=True)
    if verbosity is not Verbosity.NONE:
        print_total(output_record, verbosity)


def process(
    fpath,
    *,
    output,
    convert=False,
    image_extensions=None,
    jpeg_quality=75,
    tiff_quality=75,
    optimize=True,
):
    """
    Attempts to convert and/or compress the images found in the Office File

    Args:
        fpath: File path for the Office File

    Kwargs:
        output: File path for the compressed output.
        convert: Convert TIFFs to JPEGs. Default is False
        image_extensions: Supported image extensions. Deafult is None which
                          will use only the supported extensions that
                          can be OPENd and SAVEd by PIL on your machine.
        jpeg_quality: Defaults to 75, which is PIL's default quality value
                 Only applicable to JPEG and TIFFs
        tiff_quality: Defaults to 75.
        optimize: Defaults to True.
                  If true, an optimization pass will be attempted
                  Will be applied to JPEG and PNGs only

    Returns:
        CompressionRecord: namedtuple of the results
    """
    if image_extensions is None:
        registered_extensions = Image.registered_extensions()
        image_extensions = {
            ext for ext, func in registered_extensions.items()
            if func in Image.SAVE
            if func in Image.OPEN
        }
    num_images_compressed = 0
    num_images_converted = 0
    num_images_skipped = 0
    start_size = os.stat(fpath).st_size
    errors = []
    conversions = []

    with zipfile.ZipFile(fpath, 'r') as in_zip:
        with tempfile.NamedTemporaryFile(mode='rb+') as tmp_file:
            with zipfile.ZipFile(tmp_file, 'w') as out_zip:
                out_zip.comment = in_zip.comment
                for item in in_zip.infolist():
                    fname, ext = os.path.splitext(item.filename)
                    ext = ext.lower()
                    if convert and (ext == '.xml' or ext == '.rels'):
                        continue
                    if convert and ext == '.tiff':
                        out_arcname = f'{fname}.jpeg'
                        try:
                            conversions.append(
                                (
                                    os.path.split(item.filename)[1].encode(),
                                    os.path.split(out_arcname)[1].encode()
                                )
                            )
                        except UnicodeError:
                            errors.append(
                                f'ERROR: Could not encode {item.filename} '
                                f'and/or {out_arcname}. '
                                'Conversion and compression will be skipped.'
                            )
                            num_images_skipped += 1
                            out_zip.writestr(item, in_zip.read(item.filename))
                        else:
                            try:
                                converted_image = convert_image(
                                    in_zip.read(item.filename)
                                )
                            except Exception as e:
                                errors.append(
                                    'ERROR: Could not convert '
                                    f'{item.filename}. Conversion and '
                                    f'compression will be skipped.\n{str(e)}'
                                )
                                num_images_skipped += 1
                                out_zip.writestr(
                                    item, in_zip.read(item.filename)
                                )
                            else:
                                num_images_converted += 1
                                converted_image.seek(0)
                                out_zip.writestr(
                                    out_arcname, converted_image.read()
                                )
                    elif ext in image_extensions:
                        try:
                            compressed_image = compress_image(
                                in_zip.read(item.filename)
                            )
                        except Exception as e:
                            errors.append(
                                f'ERROR: Could not compress {item.filename}: '
                                f'{str(e)}'
                            )
                            num_images_skipped += 1
                            out_zip.writestr(item, in_zip.read(item.filename))
                        else:
                            if item.file_size > compressed_image.tell() > 0:
                                num_images_compressed += 1
                                compressed_image.seek(0)
                                out_zip.writestr(item, compressed_image.read())
                            else:
                                num_images_skipped += 1
                                out_zip.writestr(
                                    item, in_zip.read(item.filename)
                                )
                    else:
                        out_zip.writestr(item, in_zip.read(item.filename))
                if convert and conversions:
                    for item in in_zip.infolist():
                        ext = os.path.splitext(item.filename)[1].lower()
                        if ext == '.xml' or ext == '.rels':
                            out_xml = in_zip.read(item.filename)
                            for orig_image, converted_image in conversions:
                                out_xml = out_xml.replace(
                                    orig_image, converted_image
                                )
                            out_zip.writestr(item, out_xml)
            with open(output, 'wb') as f:
                tmp_file.seek(0)
                f.write(tmp_file.read())
    return CompressionRecord(
        filename=fpath,
        errors=errors,
        num_images_compressed=num_images_compressed,
        num_images_converted=num_images_converted,
        num_images_skipped=num_images_skipped,
        start_size=start_size,
        compressed_size=os.stat(output).st_size,
    )


def compress_image(
    image_bytes,
    jpeg_quality=75,
    tiff_quality=75,
    optimize=True,
):
    """
    Compresses image if it is of a format of JPEG, PNG, or TIFF.

    Args:
        image: image to be compressed as bytes

    Kwargs:
        jpeg_quality: Defaults to 75, which is PIL's
                      default quality value for JPEGs
        tiff_quality: Defaults to 75.
        optimize: Defaults to True.
                  If true, an optimization pass will be attempted

    Returns:
        io.BytesIO object positioned at the last write
    """
    bytes_io_image = io.BytesIO()
    pil_image = Image.open(io.BytesIO(image_bytes))
    if pil_image.format == 'JPEG':
        pil_image.save(
            bytes_io_image,
            format='JPEG',
            quality=jpeg_quality,
            optimize=optimize,
        )
    elif pil_image.format == 'PNG':
        pil_image.save(bytes_io_image, format='PNG', optimize=optimize)
    elif pil_image.format == 'TIFF':
        pil_image.save(bytes_io_image, format='TIFF', quality=tiff_quality)
    return bytes_io_image


def convert_image(image_bytes, quality=75, optimize=True):
    """
    Converts image to JPG

    Args:
        image: image to be converted as bytes

    Kwargs:
        quality: Defaults to 75, which is PIL's
                 default quality value for JPEGs
        optimize: Defaults to True.
                  If true, an optimization pass will be attempted

    Returns:
        io.BytesIO object positioned at the last write
    """
    bytes_io_image = io.BytesIO()
    pil_image = Image.open(io.BytesIO(image_bytes))
    pil_image = pil_image.convert('RGB')
    pil_image.save(
        bytes_io_image, 'JPEG', quality=quality, optimize=optimize
    )
    return bytes_io_image


def printer(future, verbosity=Verbosity.NORMAL):
    try:
        result = future.result()
    except Exception as e:
        print(e)
    else:
        plural_errors = '' if len(result.errors) == 1 else 's'
        if verbosity is Verbosity.LOW:
            if result.num_images_compressed:
                print(
                    f'Compressed {result.filename!r}. '
                    f'{len(result.errors):,} Error{plural_errors} encountered.'
                )
        elif verbosity is Verbosity.NORMAL:
            if result.num_images_compressed:
                print(
                    f'Filename: {result.filename!r}.'
                    '\n'
                    f'Results: '
                    f'{result.num_images_compressed:,} compressed, '
                    f'{result.num_images_converted:,} converted, '
                    f'{result.num_images_skipped:,} skipped'
                    '\n'
                    f'Errors: {len(result.errors):,}'
                )
            else:
                print(
                    f'No images compressed for {result.filename!r}. '
                    f'{len(result.errors):,} Error{plural_errors} encountered.'
                )
        elif verbosity is Verbosity.HIGH:
            errors = ", ".join(result.errors) if result.errors else 'None!'
            print(
                ''.join(
                    [
                        f'Filename: {result.filename!r}.',
                        '\n',
                        'Results: ',
                        f'\n\t{result.num_images_compressed:,} compressed',
                        f'\n\t{result.num_images_converted:,} converted',
                        f'\n\t{result.num_images_skipped:,} skipped',
                        '\n',
                        f'Errors:\n\t{errors}'
                    ]
                )
            )


def totaler(output_record, future):
    try:
        result = future.result()
    except Exception as e:
        output_record['errors'].append(str(e))
    else:
        total_images = sum(
            [
                result.num_images_compressed,
                result.num_images_converted,
                result.num_images_skipped,
            ]
        )
        output_record['compressed_files'].append(result.filename)
        output_record['images_total'] += total_images
        output_record['images_compressed'] += result.num_images_compressed
        output_record['images_skipped'] += result.num_images_skipped
        output_record['images_converted'] += result.num_images_converted
        output_record['total_bytes'] += result.start_size
        output_record['total_bytes_compressed'] += result.compressed_size
        output_record['image_errors'].extend(result.errors)


def print_total(record, verbosity):
    print('\n\n')
    plural_files = '' if len(record['compressed_files']) == 1 else 's'
    plural_imgs = '' if record['images_compressed'] == 1 else 's'
    plural_converted = '' if record['images_converted'] == 1 else 's'
    plural_img_errs = '' if record['image_errors'] == 1 else 's'
    plural_errs = '' if len(record['errors']) == 1 else 's'
    if verbosity is Verbosity.LOW:
        print(
            f'Compressed {len(record["compressed_files"]):,} '
            f'document{plural_files} with '
            f'{len(record["image_errors"]):,} '
            f'image{plural_img_errs} that could not be converted and '
            f'{len(record["errors"]):,} document{plural_errs} '
            'that failed.'
        )
    elif verbosity is Verbosity.NORMAL:
        if record['total_bytes_compressed'] > 0:
            gb = 1024 * 1024 * 1024
            mb = 1024 * 1024
            kb = 1024
            total_cmp = record['total_bytes_compressed']
            if total_cmp > gb:
                savings = f'{total_cmp / gb:.2f} GB'
            elif total_cmp > mb:
                savings = f'{total_cmp / mb:.2f} MB'
            elif total_cmp > kb:
                savings = f'{total_cmp / kb:.2f} KB'
            else:
                if total_cmp < 1:
                    total_cmp = '<1'
                savings = f'{total_cmp} bytes'
            output = f'Compressed {len(record["compressed_files"]):,} '
            output += f'document{plural_files}\n'
            output += f'{record["images_compressed"]:,} '
            output += f'image{plural_imgs} were '
            output += f'compressed for a savings of {savings}'
            output += '\n'
            if record['images_converted'] > 0:
                output += f'{record["images_converted"]:,} '
                output += f'image{plural_converted} were '
                output += 'converted from TIFF to JPG\n'
            if record['image_errors']:
                output += f'{len(record["image_errors"]):,} '
                output += f'image{plural_img_errs} could not be '
                output += 'converted or compressed\n'
            if record['errors']:
                output += f'{len(record["errors"]):,} '
                output += f'document{plural_errs} '
                output += 'could not be compressed due to error'
        else:
            output = 'No images were compressed'
        print(output)
    elif verbosity is Verbosity.HIGH:
        if record['total_bytes_compressed'] > 0:
            gb = 1024 * 1024 * 1024
            mb = 1024 * 1024
            kb = 1024
            total_cmp = record['total_bytes_compressed']
            if total_cmp > gb:
                savings = f'{total_cmp / gb:.2f} GB'
            elif total_cmp > mb:
                savings = f'{total_cmp / mb:.2f} MB'
            elif total_cmp > kb:
                savings = f'{total_cmp / kb:.2f} KB'
            else:
                if total_cmp < 1:
                    total_cmp = '<1'
                savings = f'{total_cmp} bytes'
            output = f'Compressed {len(record["compressed_files"]):,} '
            output += f'document{plural_files}:\n\t'
            output += '\n\t'.join(record['compressed_files'])
            output += f'\n{record["images_compressed"]:,} '
            output += f'image{plural_imgs} were '
            output += f'compressed for a savings of {savings}'
            output += '\n'
            if record['images_converted'] > 0:
                output += f'{record["images_converted"]:,} '
                output += f'image{plural_converted} were converted '
                output += 'from TIFF to JPG\n'
            if record['image_errors']:
                output += f'{len(record["image_errors"]):,} '
                output += f'image{plural_img_errs} could not be '
                output += 'converted or compressed\n'
            if record['errors']:
                output += 'ERRORS:\n\t'
                output += '\n\t'.join(record["errors"])
            else:
                output += 'No errors received!'
        else:
            output = 'No images were compressed'
        print(output)
