// Decode decodes an array of bytes into an object.
//  - fPort contains the LoRaWAN fPort number
//  - bytes is an array of bytes, e.g. [225, 230, 255, 0]
// The function must return an object, e.g. {"temperature": 22.5}

function Decode(fPort, bytes, variables) {
    // Decode an uplink message from a buffer (array) of bytes to an object of fields.
    var decoded = {};

    function toSignedInt16(high, low) {
        var value = (high << 8) | low;
        if (value & 0x8000) {
            value = -(0x10000 - value);
        }
        return value;
    }

    function toSignedInt24(byte1, byte2, byte3) {
        var value = (byte1 << 16) | (byte2 << 8) | byte3;
        if (value & 0x800000) {
            value = -(0x1000000 - value);
        }
        return value;
    }

    if (bytes.length === 18) {
        // Decode GPS data
        decoded.latitude = toSignedInt24(bytes[0], bytes[1], bytes[2]) / 10000.0;
        decoded.longitude = toSignedInt24(bytes[3], bytes[4], bytes[5]) / 10000.0;

        // Decode acceleration data
        decoded.acceleration_x = toSignedInt16(bytes[7], bytes[8]) / 1000.0;
        decoded.acceleration_y = toSignedInt16(bytes[9], bytes[10]) / 1000.0;
        decoded.acceleration_z = toSignedInt16(bytes[11], bytes[12]) / 1000.0;

        // Decode temperature
        decoded.temperature = toSignedInt16(bytes[14], bytes[15]) / 10.0;

        // Decode battery level
        decoded.battery = (bytes[16] << 8 | bytes[17]) * 10.0;
    }

    return decoded;
}