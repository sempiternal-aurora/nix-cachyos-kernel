{
  inputs,
  callPackage,
  lib,
  linuxKernel,
  ...
}:
let
  helpers = callPackage ../helpers.nix { };
  inherit (helpers) kernelModuleLLVMOverride;

  kernels = lib.filterAttrs (_: lib.isDerivation) (callPackage ./. { inherit inputs; });
in
lib.mapAttrs' (
  n: v:
  let
    packages = kernelModuleLLVMOverride (
      (linuxKernel.packagesFor v).extend (
        final: prev:
        let
          zfsVariant = lib.removePrefix "linux-cachyos-" v.cachyosConfigVariant;
          zfsPackages = final.callPackage ../zfs-cachyos {
            inherit inputs;
          };
        in
        {
          zfs_cachyos = zfsPackages."${zfsVariant}" or zfsPackages.latest;
        }
      )
    );
  in
  lib.nameValuePair "linuxPackages-${lib.removePrefix "linux-" n}" packages
) kernels
